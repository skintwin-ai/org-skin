"""
Data Store

Persistent storage for organization data using JSON files and SQLite.
"""

import json
import sqlite3
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, TypeVar, Generic, Type
from contextlib import contextmanager
import logging

from org_skin.db.models import (
    BaseData, OrgData, RepoData, EntityData, WorkflowData,
    PatternData, AnalysisData, SyncRecord, SyncStatus, INDEXES
)

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseData)


class Collection(Generic[T]):
    """
    A collection of data items with CRUD operations.
    
    Provides a simple interface for storing and retrieving data items.
    """
    
    def __init__(
        self,
        store: "DataStore",
        name: str,
        model_class: Type[T],
    ):
        """
        Initialize a collection.
        
        Args:
            store: Parent data store.
            name: Collection name.
            model_class: Data model class.
        """
        self.store = store
        self.name = name
        self.model_class = model_class
        self._cache: dict[str, T] = {}
    
    def get(self, id: str) -> Optional[T]:
        """Get an item by ID."""
        if id in self._cache:
            return self._cache[id]
        
        data = self.store._load_item(self.name, id)
        if data:
            item = self._deserialize(data)
            self._cache[id] = item
            return item
        return None
    
    def get_all(self) -> list[T]:
        """Get all items in the collection."""
        items = []
        for data in self.store._load_all(self.name):
            item = self._deserialize(data)
            self._cache[item.id] = item
            items.append(item)
        return items
    
    def find(self, **kwargs) -> list[T]:
        """Find items matching criteria."""
        results = []
        for item in self.get_all():
            match = True
            for key, value in kwargs.items():
                if getattr(item, key, None) != value:
                    match = False
                    break
            if match:
                results.append(item)
        return results
    
    def find_one(self, **kwargs) -> Optional[T]:
        """Find first item matching criteria."""
        results = self.find(**kwargs)
        return results[0] if results else None
    
    def save(self, item: T) -> None:
        """Save an item."""
        item.updated_at = datetime.now()
        item.checksum = item.compute_checksum()
        
        self._cache[item.id] = item
        self.store._save_item(self.name, item.id, self._serialize(item))
    
    def delete(self, id: str) -> bool:
        """Delete an item by ID."""
        if id in self._cache:
            del self._cache[id]
        return self.store._delete_item(self.name, id)
    
    def count(self) -> int:
        """Count items in the collection."""
        return self.store._count_items(self.name)
    
    def clear(self) -> None:
        """Clear all items in the collection."""
        self._cache.clear()
        self.store._clear_collection(self.name)
    
    def _serialize(self, item: T) -> dict[str, Any]:
        """Serialize an item to dictionary."""
        return item.to_dict()
    
    def _deserialize(self, data: dict[str, Any]) -> T:
        """Deserialize a dictionary to an item."""
        # Handle datetime fields
        for field in ['created_at', 'updated_at', 'pushed_at', 'last_run', 
                      'last_matched', 'started_at', 'completed_at']:
            if field in data and data[field] and isinstance(data[field], str):
                try:
                    data[field] = datetime.fromisoformat(data[field])
                except ValueError:
                    data[field] = None
        
        # Handle enum fields
        if 'sync_status' in data:
            data['sync_status'] = SyncStatus(data['sync_status'])
        
        return self.model_class(**data)


class DataStore:
    """
    Persistent data store for organization data.
    
    Features:
    - JSON file-based storage
    - SQLite index for fast queries
    - Collection-based API
    - Automatic versioning
    - Checksum validation
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize the data store.
        
        Args:
            data_dir: Directory for data storage.
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize SQLite for indexing
        self.db_path = self.data_dir / "index.db"
        self._init_db()
        
        # Initialize collections
        self.organizations = Collection(self, "organizations", OrgData)
        self.repositories = Collection(self, "repositories", RepoData)
        self.entities = Collection(self, "entities", EntityData)
        self.workflows = Collection(self, "workflows", WorkflowData)
        self.patterns = Collection(self, "patterns", PatternData)
        self.analyses = Collection(self, "analyses", AnalysisData)
        self.sync_records = Collection(self, "sync_records", SyncRecord)
    
    def _init_db(self) -> None:
        """Initialize SQLite database for indexing."""
        with self._get_db() as conn:
            cursor = conn.cursor()
            
            # Create index table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS item_index (
                    collection TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    field TEXT NOT NULL,
                    value TEXT,
                    PRIMARY KEY (collection, item_id, field)
                )
            """)
            
            # Create metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_db(self):
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            yield conn
        finally:
            conn.close()
    
    def _get_collection_dir(self, collection: str) -> Path:
        """Get directory for a collection."""
        path = self.data_dir / collection
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def _load_item(self, collection: str, id: str) -> Optional[dict[str, Any]]:
        """Load an item from storage."""
        file_path = self._get_collection_dir(collection) / f"{id}.json"
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        return None
    
    def _load_all(self, collection: str) -> list[dict[str, Any]]:
        """Load all items from a collection."""
        items = []
        collection_dir = self._get_collection_dir(collection)
        for file_path in collection_dir.glob("*.json"):
            with open(file_path, 'r') as f:
                items.append(json.load(f))
        return items
    
    def _save_item(self, collection: str, id: str, data: dict[str, Any]) -> None:
        """Save an item to storage."""
        file_path = self._get_collection_dir(collection) / f"{id}.json"
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        # Update index
        self._update_index(collection, id, data)
    
    def _delete_item(self, collection: str, id: str) -> bool:
        """Delete an item from storage."""
        file_path = self._get_collection_dir(collection) / f"{id}.json"
        if file_path.exists():
            file_path.unlink()
            self._remove_from_index(collection, id)
            return True
        return False
    
    def _count_items(self, collection: str) -> int:
        """Count items in a collection."""
        collection_dir = self._get_collection_dir(collection)
        return len(list(collection_dir.glob("*.json")))
    
    def _clear_collection(self, collection: str) -> None:
        """Clear all items in a collection."""
        collection_dir = self._get_collection_dir(collection)
        for file_path in collection_dir.glob("*.json"):
            file_path.unlink()
        
        # Clear index
        with self._get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM item_index WHERE collection = ?",
                (collection,)
            )
            conn.commit()
    
    def _update_index(self, collection: str, id: str, data: dict[str, Any]) -> None:
        """Update index for an item."""
        index_fields = INDEXES.get(collection.rstrip('s') + '_data', [])
        
        with self._get_db() as conn:
            cursor = conn.cursor()
            
            # Remove old index entries
            cursor.execute(
                "DELETE FROM item_index WHERE collection = ? AND item_id = ?",
                (collection, id)
            )
            
            # Add new index entries
            for field in index_fields:
                value = data.get(field)
                if value is not None:
                    cursor.execute(
                        "INSERT INTO item_index (collection, item_id, field, value) VALUES (?, ?, ?, ?)",
                        (collection, id, field, str(value))
                    )
            
            conn.commit()
    
    def _remove_from_index(self, collection: str, id: str) -> None:
        """Remove item from index."""
        with self._get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM item_index WHERE collection = ? AND item_id = ?",
                (collection, id)
            )
            conn.commit()
    
    def query(
        self,
        collection: str,
        field: str,
        value: str,
    ) -> list[str]:
        """Query items by indexed field."""
        with self._get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT item_id FROM item_index WHERE collection = ? AND field = ? AND value = ?",
                (collection, field, value)
            )
            return [row[0] for row in cursor.fetchall()]
    
    def get_metadata(self, key: str) -> Optional[str]:
        """Get metadata value."""
        with self._get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM metadata WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
    
    def set_metadata(self, key: str, value: str) -> None:
        """Set metadata value."""
        with self._get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                (key, value)
            )
            conn.commit()
    
    def export_all(self, output_file: str) -> None:
        """Export all data to a single JSON file."""
        data = {
            "organizations": [o.to_dict() for o in self.organizations.get_all()],
            "repositories": [r.to_dict() for r in self.repositories.get_all()],
            "entities": [e.to_dict() for e in self.entities.get_all()],
            "workflows": [w.to_dict() for w in self.workflows.get_all()],
            "patterns": [p.to_dict() for p in self.patterns.get_all()],
            "analyses": [a.to_dict() for a in self.analyses.get_all()],
            "exported_at": datetime.now().isoformat(),
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Exported all data to {output_file}")
    
    def import_all(self, input_file: str) -> None:
        """Import all data from a JSON file."""
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        # Import organizations
        for org_data in data.get("organizations", []):
            org = OrgData(**org_data)
            self.organizations.save(org)
        
        # Import repositories
        for repo_data in data.get("repositories", []):
            repo = RepoData(**repo_data)
            self.repositories.save(repo)
        
        # Import entities
        for entity_data in data.get("entities", []):
            entity = EntityData(**entity_data)
            self.entities.save(entity)
        
        # Import workflows
        for workflow_data in data.get("workflows", []):
            workflow = WorkflowData(**workflow_data)
            self.workflows.save(workflow)
        
        # Import patterns
        for pattern_data in data.get("patterns", []):
            pattern = PatternData(**pattern_data)
            self.patterns.save(pattern)
        
        # Import analyses
        for analysis_data in data.get("analyses", []):
            analysis = AnalysisData(**analysis_data)
            self.analyses.save(analysis)
        
        logger.info(f"Imported data from {input_file}")
    
    def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        return {
            "organizations": self.organizations.count(),
            "repositories": self.repositories.count(),
            "entities": self.entities.count(),
            "workflows": self.workflows.count(),
            "patterns": self.patterns.count(),
            "analyses": self.analyses.count(),
            "sync_records": self.sync_records.count(),
            "data_dir": str(self.data_dir),
            "db_path": str(self.db_path),
        }
