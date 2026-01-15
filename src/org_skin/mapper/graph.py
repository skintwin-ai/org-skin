"""
Organization Graph

Graph-based representation of organization entities and relationships.
Supports hypergraph operations for complex multi-entity relationships.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Optional, Iterator
from collections import defaultdict
import logging

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

from org_skin.mapper.entities import (
    BaseEntity, EntityType, Relationship, RelationType
)

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    """Represents a node in the organization graph."""
    id: str
    entity_type: EntityType
    data: dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if isinstance(other, GraphNode):
            return self.id == other.id
        return False


@dataclass
class GraphEdge:
    """Represents an edge in the organization graph."""
    source_id: str
    target_id: str
    relation_type: RelationType
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash((self.source_id, self.target_id, self.relation_type))
    
    def __eq__(self, other):
        if isinstance(other, GraphEdge):
            return (
                self.source_id == other.source_id and
                self.target_id == other.target_id and
                self.relation_type == other.relation_type
            )
        return False


@dataclass
class HyperEdge:
    """
    Represents a hyperedge connecting multiple entities.
    
    Used for complex relationships like:
    - Team maintains multiple repositories
    - Multiple members collaborate on a project
    - Cross-repository dependencies
    """
    id: str
    entity_ids: list[str]
    relation_type: str
    metadata: dict[str, Any] = field(default_factory=dict)


class OrgGraph:
    """
    Graph representation of an organization.
    
    Features:
    - Entity storage and retrieval
    - Relationship management
    - Graph traversal
    - Hyperedge support for multi-entity relationships
    - Export to various formats
    """
    
    def __init__(self):
        """Initialize the organization graph."""
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        self.hyperedges: list[HyperEdge] = []
        
        # Indexes for fast lookup
        self._nodes_by_type: dict[EntityType, list[str]] = defaultdict(list)
        self._edges_by_source: dict[str, list[GraphEdge]] = defaultdict(list)
        self._edges_by_target: dict[str, list[GraphEdge]] = defaultdict(list)
        self._edges_by_type: dict[RelationType, list[GraphEdge]] = defaultdict(list)
        
        # NetworkX graph for advanced operations
        self._nx_graph: Optional[Any] = None
        if HAS_NETWORKX:
            self._nx_graph = nx.DiGraph()
    
    def add_entity(self, entity: BaseEntity) -> None:
        """Add an entity to the graph."""
        node = GraphNode(
            id=entity.id,
            entity_type=entity.entity_type,
            data=entity.to_dict(),
        )
        self.nodes[entity.id] = node
        self._nodes_by_type[entity.entity_type].append(entity.id)
        
        if self._nx_graph is not None:
            self._nx_graph.add_node(
                entity.id,
                entity_type=entity.entity_type.value,
                **entity.to_dict()
            )
    
    def add_relationship(self, relationship: Relationship) -> None:
        """Add a relationship to the graph."""
        edge = GraphEdge(
            source_id=relationship.source_id,
            target_id=relationship.target_id,
            relation_type=relationship.relation_type,
            metadata=relationship.metadata,
        )
        self.edges.append(edge)
        self._edges_by_source[relationship.source_id].append(edge)
        self._edges_by_target[relationship.target_id].append(edge)
        self._edges_by_type[relationship.relation_type].append(edge)
        
        if self._nx_graph is not None:
            self._nx_graph.add_edge(
                relationship.source_id,
                relationship.target_id,
                relation_type=relationship.relation_type.value,
                **relationship.metadata
            )
    
    def add_hyperedge(
        self,
        entity_ids: list[str],
        relation_type: str,
        metadata: dict[str, Any] = None,
    ) -> HyperEdge:
        """Add a hyperedge connecting multiple entities."""
        hyperedge = HyperEdge(
            id=f"he_{len(self.hyperedges)}",
            entity_ids=entity_ids,
            relation_type=relation_type,
            metadata=metadata or {},
        )
        self.hyperedges.append(hyperedge)
        return hyperedge
    
    def get_entity(self, entity_id: str) -> Optional[GraphNode]:
        """Get an entity by ID."""
        return self.nodes.get(entity_id)
    
    def get_entities_by_type(self, entity_type: EntityType) -> list[GraphNode]:
        """Get all entities of a specific type."""
        return [self.nodes[id] for id in self._nodes_by_type.get(entity_type, [])]
    
    def get_relationships_from(self, entity_id: str) -> list[GraphEdge]:
        """Get all relationships originating from an entity."""
        return self._edges_by_source.get(entity_id, [])
    
    def get_relationships_to(self, entity_id: str) -> list[GraphEdge]:
        """Get all relationships targeting an entity."""
        return self._edges_by_target.get(entity_id, [])
    
    def get_relationships_by_type(self, relation_type: RelationType) -> list[GraphEdge]:
        """Get all relationships of a specific type."""
        return self._edges_by_type.get(relation_type, [])
    
    def get_neighbors(
        self,
        entity_id: str,
        direction: str = "both",
    ) -> list[GraphNode]:
        """
        Get neighboring entities.
        
        Args:
            entity_id: Source entity ID.
            direction: "outgoing", "incoming", or "both".
            
        Returns:
            List of neighboring nodes.
        """
        neighbor_ids = set()
        
        if direction in ("outgoing", "both"):
            for edge in self._edges_by_source.get(entity_id, []):
                neighbor_ids.add(edge.target_id)
        
        if direction in ("incoming", "both"):
            for edge in self._edges_by_target.get(entity_id, []):
                neighbor_ids.add(edge.source_id)
        
        return [self.nodes[id] for id in neighbor_ids if id in self.nodes]
    
    def find_path(
        self,
        source_id: str,
        target_id: str,
    ) -> Optional[list[str]]:
        """Find shortest path between two entities."""
        if self._nx_graph is not None:
            try:
                return nx.shortest_path(self._nx_graph, source_id, target_id)
            except nx.NetworkXNoPath:
                return None
        
        # Simple BFS fallback
        from collections import deque
        
        visited = {source_id}
        queue = deque([(source_id, [source_id])])
        
        while queue:
            current, path = queue.popleft()
            
            if current == target_id:
                return path
            
            for neighbor in self.get_neighbors(current, "outgoing"):
                if neighbor.id not in visited:
                    visited.add(neighbor.id)
                    queue.append((neighbor.id, path + [neighbor.id]))
        
        return None
    
    def get_subgraph(
        self,
        entity_ids: list[str],
        include_relationships: bool = True,
    ) -> "OrgGraph":
        """Extract a subgraph containing specified entities."""
        subgraph = OrgGraph()
        
        for entity_id in entity_ids:
            if entity_id in self.nodes:
                # Create a minimal entity for the subgraph
                node = self.nodes[entity_id]
                from org_skin.mapper.entities import BaseEntity
                entity = BaseEntity(
                    id=node.id,
                    entity_type=node.entity_type,
                    metadata=node.data,
                )
                subgraph.add_entity(entity)
        
        if include_relationships:
            entity_set = set(entity_ids)
            for edge in self.edges:
                if edge.source_id in entity_set and edge.target_id in entity_set:
                    rel = Relationship(
                        source_id=edge.source_id,
                        target_id=edge.target_id,
                        relation_type=edge.relation_type,
                        metadata=edge.metadata,
                    )
                    subgraph.add_relationship(rel)
        
        return subgraph
    
    def compute_centrality(self) -> dict[str, float]:
        """Compute centrality scores for all entities."""
        if self._nx_graph is not None and len(self._nx_graph) > 0:
            return nx.degree_centrality(self._nx_graph)
        
        # Simple degree-based centrality fallback
        centrality = {}
        for entity_id in self.nodes:
            degree = (
                len(self._edges_by_source.get(entity_id, [])) +
                len(self._edges_by_target.get(entity_id, []))
            )
            centrality[entity_id] = degree / max(len(self.nodes) - 1, 1)
        
        return centrality
    
    def find_clusters(self) -> list[set[str]]:
        """Find connected components (clusters) in the graph."""
        if self._nx_graph is not None:
            return [
                set(component)
                for component in nx.weakly_connected_components(self._nx_graph)
            ]
        
        # Simple DFS-based clustering fallback
        visited = set()
        clusters = []
        
        def dfs(node_id: str, cluster: set):
            visited.add(node_id)
            cluster.add(node_id)
            for neighbor in self.get_neighbors(node_id, "both"):
                if neighbor.id not in visited:
                    dfs(neighbor.id, cluster)
        
        for node_id in self.nodes:
            if node_id not in visited:
                cluster = set()
                dfs(node_id, cluster)
                clusters.append(cluster)
        
        return clusters
    
    def to_dict(self) -> dict[str, Any]:
        """Convert graph to dictionary representation."""
        return {
            "nodes": [
                {
                    "id": node.id,
                    "entity_type": node.entity_type.value,
                    "data": node.data,
                }
                for node in self.nodes.values()
            ],
            "edges": [
                {
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "relation_type": edge.relation_type.value,
                    "metadata": edge.metadata,
                }
                for edge in self.edges
            ],
            "hyperedges": [
                {
                    "id": he.id,
                    "entity_ids": he.entity_ids,
                    "relation_type": he.relation_type,
                    "metadata": he.metadata,
                }
                for he in self.hyperedges
            ],
            "statistics": {
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
                "hyperedge_count": len(self.hyperedges),
                "nodes_by_type": {
                    k.value: len(v) for k, v in self._nodes_by_type.items()
                },
            },
        }
    
    def to_json(self, filepath: str) -> None:
        """Export graph to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def to_graphml(self, filepath: str) -> None:
        """Export graph to GraphML format."""
        if self._nx_graph is None:
            raise RuntimeError("NetworkX is required for GraphML export")
        
        nx.write_graphml(self._nx_graph, filepath)
    
    def to_mermaid(self) -> str:
        """Generate Mermaid diagram representation."""
        lines = ["graph TD"]
        
        # Add nodes with labels
        for node in self.nodes.values():
            label = node.data.get("name", node.data.get("login", node.id[:8]))
            node_type = node.entity_type.value[:3].upper()
            lines.append(f'    {node.id[:8]}["{node_type}: {label}"]')
        
        # Add edges
        for edge in self.edges:
            source = edge.source_id[:8]
            target = edge.target_id[:8]
            label = edge.relation_type.value
            lines.append(f'    {source} -->|{label}| {target}')
        
        return "\n".join(lines)
    
    def __len__(self) -> int:
        return len(self.nodes)
    
    def __iter__(self) -> Iterator[GraphNode]:
        return iter(self.nodes.values())
    
    def __contains__(self, entity_id: str) -> bool:
        return entity_id in self.nodes
