"""
Chat Session Management

Manages conversation state and history for multi-turn dialogues.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class MessageRole(Enum):
    """Message roles in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """Represents a message in a conversation."""
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ConversationContext:
    """Context information for a conversation."""
    current_repo: Optional[str] = None
    current_org: str = "skintwin-ai"
    last_query_type: Optional[str] = None
    last_entities: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "current_repo": self.current_repo,
            "current_org": self.current_org,
            "last_query_type": self.last_query_type,
            "last_entities": self.last_entities,
            "variables": self.variables,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationContext":
        return cls(
            current_repo=data.get("current_repo"),
            current_org=data.get("current_org", "skintwin-ai"),
            last_query_type=data.get("last_query_type"),
            last_entities=data.get("last_entities", {}),
            variables=data.get("variables", {}),
        )


class ChatSession:
    """
    Manages a chat session with conversation history and context.
    
    Features:
    - Message history tracking
    - Context management
    - Session persistence
    - Multi-turn dialogue support
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        max_history: int = 100,
    ):
        """
        Initialize a chat session.
        
        Args:
            session_id: Unique session identifier. Generated if not provided.
            max_history: Maximum number of messages to keep in history.
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.max_history = max_history
        self.messages: list[Message] = []
        self.context = ConversationContext()
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
    
    def add_message(self, message: Message) -> None:
        """Add a message to the conversation history."""
        self.messages.append(message)
        self.last_activity = datetime.now()
        
        # Trim history if needed
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]
        
        # Update context based on message
        self._update_context(message)
    
    def _update_context(self, message: Message) -> None:
        """Update context based on a new message."""
        if message.role == MessageRole.USER:
            # Extract entities from user message
            content = message.content.lower()
            
            # Check for repository mentions
            import re
            repo_match = re.search(r'repo(?:sitory)?\s+(\w+[-\w]*)', content)
            if repo_match:
                self.context.current_repo = repo_match.group(1)
            
            # Check for organization mentions
            org_match = re.search(r'org(?:anization)?\s+(\w+[-\w]*)', content)
            if org_match:
                self.context.current_org = org_match.group(1)
        
        # Store metadata from assistant responses
        if message.role == MessageRole.ASSISTANT and message.metadata:
            if "aiml_pattern" in message.metadata:
                self.context.last_query_type = message.metadata["aiml_pattern"]
    
    def get_history(
        self,
        limit: Optional[int] = None,
        role: Optional[MessageRole] = None,
    ) -> list[Message]:
        """
        Get conversation history.
        
        Args:
            limit: Maximum number of messages to return.
            role: Filter by message role.
            
        Returns:
            List of messages.
        """
        messages = self.messages
        
        if role:
            messages = [m for m in messages if m.role == role]
        
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    def get_context(self) -> dict[str, Any]:
        """Get current conversation context."""
        return self.context.to_dict()
    
    def set_context_variable(self, key: str, value: Any) -> None:
        """Set a context variable."""
        self.context.variables[key] = value
    
    def get_context_variable(self, key: str, default: Any = None) -> Any:
        """Get a context variable."""
        return self.context.variables.get(key, default)
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self.messages = []
    
    def reset_context(self) -> None:
        """Reset conversation context."""
        self.context = ConversationContext()
    
    def get_last_user_message(self) -> Optional[Message]:
        """Get the last user message."""
        for message in reversed(self.messages):
            if message.role == MessageRole.USER:
                return message
        return None
    
    def get_last_assistant_message(self) -> Optional[Message]:
        """Get the last assistant message."""
        for message in reversed(self.messages):
            if message.role == MessageRole.ASSISTANT:
                return message
        return None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "session_id": self.session_id,
            "messages": [m.to_dict() for m in self.messages],
            "context": self.context.to_dict(),
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatSession":
        """Create session from dictionary."""
        session = cls(
            session_id=data["session_id"],
        )
        session.messages = [Message.from_dict(m) for m in data.get("messages", [])]
        session.context = ConversationContext.from_dict(data.get("context", {}))
        session.created_at = datetime.fromisoformat(data["created_at"])
        session.last_activity = datetime.fromisoformat(data["last_activity"])
        return session
    
    def save(self, filepath: str) -> None:
        """Save session to file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> "ChatSession":
        """Load session from file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def get_conversation_summary(self) -> str:
        """Generate a summary of the conversation."""
        if not self.messages:
            return "No messages in this session."
        
        user_messages = len([m for m in self.messages if m.role == MessageRole.USER])
        assistant_messages = len([m for m in self.messages if m.role == MessageRole.ASSISTANT])
        
        duration = self.last_activity - self.created_at
        
        return f"""Session: {self.session_id[:8]}...
Messages: {len(self.messages)} ({user_messages} user, {assistant_messages} assistant)
Duration: {duration}
Current context: {self.context.current_org}/{self.context.current_repo or 'no repo'}
"""
    
    def format_for_llm(self, system_prompt: str = None) -> list[dict[str, str]]:
        """Format conversation for LLM API."""
        formatted = []
        
        if system_prompt:
            formatted.append({"role": "system", "content": system_prompt})
        
        for message in self.messages:
            formatted.append({
                "role": message.role.value,
                "content": message.content,
            })
        
        return formatted


class SessionManager:
    """Manages multiple chat sessions."""
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize session manager.
        
        Args:
            storage_dir: Directory for session persistence.
        """
        self.sessions: dict[str, ChatSession] = {}
        self.storage_dir = storage_dir
    
    def create_session(self) -> ChatSession:
        """Create a new session."""
        session = ChatSession()
        self.sessions[session.session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID."""
        return self.sessions.get(session_id)
    
    def get_or_create_session(self, session_id: str) -> ChatSession:
        """Get existing session or create new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = ChatSession(session_id=session_id)
        return self.sessions[session_id]
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def list_sessions(self) -> list[str]:
        """List all session IDs."""
        return list(self.sessions.keys())
    
    def save_all(self) -> None:
        """Save all sessions to storage."""
        if not self.storage_dir:
            return
        
        import os
        os.makedirs(self.storage_dir, exist_ok=True)
        
        for session_id, session in self.sessions.items():
            filepath = os.path.join(self.storage_dir, f"{session_id}.json")
            session.save(filepath)
    
    def load_all(self) -> None:
        """Load all sessions from storage."""
        if not self.storage_dir:
            return
        
        import os
        import glob
        
        pattern = os.path.join(self.storage_dir, "*.json")
        for filepath in glob.glob(pattern):
            try:
                session = ChatSession.load(filepath)
                self.sessions[session.session_id] = session
            except Exception as e:
                logger.error(f"Failed to load session from {filepath}: {e}")
