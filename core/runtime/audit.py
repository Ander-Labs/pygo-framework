"""PyGo Audit System (v0.34.0).

Provides audit logging, change tracking, and compliance features.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import json
import threading
from enum import Enum


class AuditAction(Enum):
    """Audit action types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"


@dataclass
class AuditEntry:
    """Represents a single audit log entry."""
    id: str
    action: AuditAction
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "action": self.action.value,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "metadata": self.metadata,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat()
        }


class AuditLog:
    """Audit log storage and query."""
    
    def __init__(self, retention_days: int = 365):
        self.entries: List[AuditEntry] = []
        self.retention_days = retention_days
        self._lock = threading.Lock()
    
    def log(self, entry: AuditEntry) -> None:
        """Log an audit entry."""
        with self._lock:
            self.entries.append(entry)
    
    def find(self, **kwargs) -> List[AuditEntry]:
        """Find audit entries by criteria."""
        with self._lock:
            results = []
            
            for entry in self.entries:
                match = True
                
                for key, value in kwargs.items():
                    if hasattr(entry, key):
                        if getattr(entry, key) != value:
                            match = False
                            break
                
                if match:
                    results.append(entry)
            
            return results
    
    def get_by_resource(self, resource_type: str, resource_id: str) -> List[AuditEntry]:
        """Get all audit entries for a resource."""
        return self.find(resource_type=resource_type, resource_id=resource_id)
    
    def export(self, format: str = "json") -> str:
        """Export audit log."""
        with self._lock:
            entries = list(self.entries)
        
        if format == "json":
            return json.dumps([e.to_dict() for e in entries], indent=2)
        elif format == "csv":
            lines = ["id,action,user_id,resource_type,resource_id,created_at"]
            for e in entries:
                lines.append(f"{e.id},{e.action.value},{e.user_id},{e.resource_type},{e.resource_id},{e.created_at.isoformat()}")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")


class AuditManager:
    """Manages audit logging across the application."""
    
    def __init__(self, retention_days: int = 365):
        self.log = AuditLog(retention_days)
        self._auditable_models: Dict[str, Any] = {}
    
    def register_model(self, model_name: str, model_class: Any) -> None:
        """Register a model for audit tracking."""
        self._auditable_models[model_name] = model_class
    
    def log_action(self, action: AuditAction, user_id: Optional[str] = None,
                   tenant_id: Optional[str] = None, resource_type: Optional[str] = None,
                   resource_id: Optional[str] = None, old_value: Optional[Dict] = None,
                   new_value: Optional[Dict] = None, metadata: Optional[Dict] = None,
                   ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> str:
        """Log an action."""
        import uuid
        
        entry = AuditEntry(
            id=str(uuid.uuid4()),
            action=action,
            user_id=user_id,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.log.log(entry)
        return entry.id


# Global audit manager
_audit_manager: Optional[AuditManager] = None


def get_audit_manager() -> AuditManager:
    """Get the global audit manager."""
    global _audit_manager
    if _audit_manager is None:
        _audit_manager = AuditManager()
    return _audit_manager


def audit(action: AuditAction, **kwargs) -> str:
    """Log an audit action."""
    return get_audit_manager().log_action(action, **kwargs)


def audit_log() -> AuditLog:
    """Get the audit log."""
    return get_audit_manager().log