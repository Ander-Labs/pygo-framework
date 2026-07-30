"""PyGo Workflow System (v0.34.0).

Provides workflow engine, state machines, and transitions.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
from datetime import datetime


class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowState:
    """Represents a state in a workflow."""
    name: str
    transitions: Dict[str, str] = field(default_factory=dict)  # action -> target_state
    entry_action: Optional[Callable] = None
    exit_action: Optional[Callable] = None


@dataclass
class WorkflowTransition:
    """Represents a transition between states."""
    from_state: str
    to_state: str
    action: str
    guard: Optional[Callable] = None
    handler: Optional[Callable] = None


class Workflow:
    """Workflow definition."""
    
    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model
        self.states: Dict[str, WorkflowState] = {}
        self.transitions: List[WorkflowTransition] = []
        self.current_state: Optional[str] = None
    
    def add_state(self, state: WorkflowState) -> "Workflow":
        """Add a state to the workflow."""
        self.states[state.name] = state
        return self
    
    def add_transition(self, transition: WorkflowTransition) -> "Workflow":
        """Add a transition to the workflow."""
        self.transitions.append(transition)
        return self
    
    def start(self, initial_state: str) -> bool:
        """Start the workflow in an initial state."""
        if initial_state not in self.states:
            return False
        
        self.current_state = initial_state
        state = self.states[initial_state]
        
        if state.entry_action:
            try:
                state.entry_action()
            except Exception as e:
                print(f"Entry action error in {initial_state}: {e}")
                return False
        
        return True
    
    def trigger(self, action: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Trigger a transition."""
        if self.current_state is None:
            return False
        
        current_state = self.states[self.current_state]
        
        # Check if action is valid in current state
        if action not in current_state.transitions:
            return False
        
        target_state = current_state.transitions[action]
        
        # Find the transition
        transition = None
        for t in self.transitions:
            if t.from_state == self.current_state and t.action == action:
                transition = t
                break
        
        if transition is None:
            return False
        
        # Check guard
        if transition.guard and not transition.guard():
            return False
        
        # Execute handler
        if transition.handler:
            try:
                transition.handler(context or {})
            except Exception as e:
                print(f"Transition handler error: {e}")
                return False
        
        # Exit current state
        current_state = self.states[self.current_state]
        if current_state.exit_action:
            try:
                current_state.exit_action()
            except Exception as e:
                print(f"Exit action error: {e}")
        
        # Enter new state
        self.current_state = target_state
        new_state = self.states[target_state]
        if new_state.entry_action:
            try:
                new_state.entry_action()
            except Exception as e:
                print(f"Entry action error in {target_state}: {e}")
                return False
        
        return True


class WorkflowInstance:
    """Running instance of a workflow."""
    
    def __init__(self, workflow: Workflow, data: Optional[Dict[str, Any]] = None):
        self.id = str(uuid.uuid4())
        self.workflow = workflow
        self.data = data or {}
        self.status = WorkflowStatus.PENDING
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.history: List[Dict[str, Any]] = []
    
    def start(self, initial_state: str) -> bool:
        """Start the workflow instance."""
        if self.workflow.start(initial_state):
            self.status = WorkflowStatus.RUNNING
            self._record_transition(None, initial_state)
            return True
        return False
    
    def trigger(self, action: str) -> bool:
        """Trigger a transition."""
        old_state = self.workflow.current_state
        if self.workflow.trigger(action, self.data):
            self._record_transition(old_state, self.workflow.current_state)
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    def _record_transition(self, from_state: Optional[str], to_state: str) -> None:
        """Record a transition in history."""
        self.history.append({
            "from": from_state,
            "to": to_state,
            "at": datetime.utcnow().isoformat()
        })
    
    def cancel(self) -> None:
        """Cancel the workflow."""
        self.status = WorkflowStatus.CANCELLED
        self.updated_at = datetime.utcnow()


class WorkflowEngine:
    """Engine for managing workflow instances."""
    
    def __init__(self):
        self.workflows: Dict[str, Workflow] = {}
        self.instances: Dict[str, WorkflowInstance] = {}
    
    def register(self, workflow: Workflow) -> None:
        """Register a workflow definition."""
        self.workflows[workflow.name] = workflow
    
    def create_instance(self, workflow_name: str, data: Optional[Dict[str, Any]] = None) -> Optional[WorkflowInstance]:
        """Create a new workflow instance."""
        if workflow_name not in self.workflows:
            return None
        
        instance = WorkflowInstance(self.workflows[workflow_name], data)
        self.instances[instance.id] = instance
        return instance
    
    def get_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        """Get a workflow instance by ID."""
        return self.instances.get(instance_id)
    
    def list_instances(self, workflow_name: Optional[str] = None) -> List[WorkflowInstance]:
        """List workflow instances."""
        if workflow_name:
            return [i for i in self.instances.values() if i.workflow.name == workflow_name]
        return list(self.instances.values())


# Global workflow engine
_engine: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    """Get the global workflow engine."""
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine


def register_workflow(workflow: Workflow) -> None:
    """Register a workflow."""
    get_workflow_engine().register(workflow)


def create_workflow(workflow_name: str, data: Optional[Dict[str, Any]] = None) -> Optional[WorkflowInstance]:
    """Create a workflow instance."""
    return get_workflow_engine().create_instance(workflow_name, data)