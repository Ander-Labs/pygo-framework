"""Test suite for v0.34.0 - Audit and Workflows."""
import pytest
from datetime import datetime

from core.runtime.audit import (
    AuditAction, AuditEntry, AuditLog, AuditManager,
    get_audit_manager, audit, audit_log
)
from core.runtime.workflows import (
    WorkflowStatus, WorkflowState, WorkflowTransition,
    Workflow, WorkflowInstance, WorkflowEngine,
    get_workflow_engine, register_workflow, create_workflow
)


# ============== Audit Tests ==============

def test_v0340_audit_action():
    """Test AuditAction enum."""
    assert AuditAction.CREATE.value == "create"
    assert AuditAction.UPDATE.value == "update"
    assert AuditAction.DELETE.value == "delete"


def test_v0340_audit_entry():
    """Test AuditEntry dataclass."""
    entry = AuditEntry(
        id="test-123",
        action=AuditAction.CREATE,
        user_id="user-1",
        resource_type="User",
        resource_id="user-123"
    )
    
    assert entry.id == "test-123"
    assert entry.action == AuditAction.CREATE
    assert entry.user_id == "user-1"


def test_v0340_audit_entry_to_dict():
    """Test AuditEntry serialization."""
    entry = AuditEntry(
        id="test-123",
        action=AuditAction.CREATE
    )
    
    data = entry.to_dict()
    assert data["id"] == "test-123"
    assert data["action"] == "create"


def test_v0340_audit_log():
    """Test AuditLog."""
    log = AuditLog()
    
    entry = AuditEntry(id="1", action=AuditAction.CREATE)
    log.log(entry)
    
    assert len(log.entries) == 1


def test_v0340_audit_log_find():
    """Test AuditLog find."""
    log = AuditLog()
    
    entry1 = AuditEntry(id="1", action=AuditAction.CREATE, resource_type="User")
    entry2 = AuditEntry(id="2", action=AuditAction.UPDATE, resource_type="Order")
    
    log.log(entry1)
    log.log(entry2)
    
    results = log.find(resource_type="User")
    assert len(results) == 1


def test_v0340_audit_log_export():
    """Test AuditLog export."""
    log = AuditLog()
    
    entry = AuditEntry(id="1", action=AuditAction.CREATE)
    log.log(entry)
    
    json_export = log.export("json")
    assert "create" in json_export
    
    csv_export = log.export("csv")
    assert "create" in csv_export


def test_v0340_audit_manager():
    """Test AuditManager."""
    manager = AuditManager()
    
    entry_id = manager.log_action(
        AuditAction.CREATE,
        user_id="user-1",
        resource_type="User",
        resource_id="user-123"
    )
    
    assert entry_id is not None


def test_v0340_global_audit_functions():
    """Test global audit functions."""
    entry_id = audit(AuditAction.CREATE, user_id="user-1")
    assert entry_id is not None
    
    log = audit_log()
    assert len(log.entries) > 0


# ============== Workflow Tests ==============

def test_v0340_workflow_state():
    """Test WorkflowState."""
    state = WorkflowState(name="draft")
    
    assert state.name == "draft"
    assert state.transitions == {}


def test_v0340_workflow_transition():
    """Test WorkflowTransition."""
    trans = WorkflowTransition(
        from_state="draft",
        to_state="published",
        action="publish"
    )
    
    assert trans.from_state == "draft"
    assert trans.to_state == "published"
    assert trans.action == "publish"


def test_v0340_workflow():
    """Test Workflow."""
    wf = Workflow("post_workflow", "Post")
    
    draft = WorkflowState(name="draft", transitions={"publish": "published"})
    published = WorkflowState(name="published", transitions={"unpublish": "draft"})
    
    wf.add_state(draft)
    wf.add_state(published)
    
    wf.add_transition(WorkflowTransition("draft", "published", "publish"))
    wf.add_transition(WorkflowTransition("published", "draft", "unpublish"))
    
    assert "draft" in wf.states
    assert "published" in wf.states


def test_v0340_workflow_start():
    """Test Workflow start."""
    wf = Workflow("test", "Test")
    wf.add_state(WorkflowState(name="pending"))
    
    assert wf.start("pending") is True
    assert wf.current_state == "pending"


def test_v0340_workflow_trigger():
    """Test Workflow trigger."""
    wf = Workflow("test", "Test")
    wf.add_state(WorkflowState(name="pending", transitions={"approve": "approved"}))
    wf.add_state(WorkflowState(name="approved"))
    
    wf.add_transition(WorkflowTransition("pending", "approved", "approve"))
    
    wf.start("pending")
    assert wf.trigger("approve") is True
    assert wf.current_state == "approved"


def test_v0340_workflow_instance():
    """Test WorkflowInstance."""
    wf = Workflow("test", "Test")
    wf.add_state(WorkflowState(name="pending"))
    wf.add_state(WorkflowState(name="approved"))
    wf.add_transition(WorkflowTransition("pending", "approved", "approve"))
    
    instance = WorkflowInstance(wf)
    
    assert instance.status == WorkflowStatus.PENDING
    assert instance.start("pending") is True
    assert instance.status == WorkflowStatus.RUNNING


def test_v0340_workflow_engine():
    """Test WorkflowEngine."""
    engine = WorkflowEngine()
    
    wf = Workflow("test", "Test")
    wf.add_state(WorkflowState(name="pending"))
    
    engine.register(wf)
    
    instance = engine.create_instance("test")
    assert instance is not None


def test_v0340_global_workflow_functions():
    """Test global workflow functions."""
    engine = get_workflow_engine()
    
    wf = Workflow("global_test", "Test")
    wf.add_state(WorkflowState(name="pending"))
    register_workflow(wf)
    
    instance = create_workflow("global_test")
    assert instance is not None