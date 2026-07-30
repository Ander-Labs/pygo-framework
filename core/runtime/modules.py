"""PyGo Module System (v0.29.0).

Provides module management, lifecycle hooks, and permissions.
"""

from __future__ import annotations

import os
import yaml
import importlib.util
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ModuleInfo:
    """Information about a PyGo module."""
    name: str
    version: str
    description: str = ""
    author: str = ""
    entry: str = "app.py"
    dependencies: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    enabled: bool = True
    
    @classmethod
    def from_yaml(cls, path: str) -> "ModuleInfo":
        """Load module info from module.yaml file."""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(
            name=data.get("name", Path(path).parent.name),
            version=data.get("version", "0.0.1"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            entry=data.get("entry", "app.py"),
            dependencies=data.get("dependencies", []),
            permissions=data.get("permissions", []),
            enabled=data.get("enabled", True)
        )


@dataclass
class Module:
    """A loaded PyGo module."""
    info: ModuleInfo
    path: Path
    _app_module: Any = None
    
    def load(self) -> bool:
        """Load the module's entry point."""
        entry_path = self.path / self.info.entry
        if not entry_path.exists():
            return False
        
        spec = importlib.util.spec_from_file_location(
            f"module_{self.info.name}",
            str(entry_path)
        )
        if spec is None or spec.loader is None:
            return False
        
        self._app_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self._app_module)
        return True
    
    def unload(self) -> None:
        """Unload the module."""
        self._app_module = None
    
    def get_handler(self, name: str) -> Any:
        """Get a handler from the module."""
        if self._app_module is None:
            return None
        return getattr(self._app_module, name, None)


class ModuleManager:
    """Manages PyGo modules."""
    
    def __init__(self, modules_dir: str = "modules"):
        self.modules_dir = Path(modules_dir)
        self.modules_dir.mkdir(exist_ok=True)
        self._modules: Dict[str, Module] = {}
        self._hooks: Dict[str, Dict[str, Any]] = {}
    
    def discover_modules(self) -> Dict[str, ModuleInfo]:
        """Discover all modules in the modules directory."""
        modules = {}
        for module_path in self.modules_dir.iterdir():
            if module_path.is_dir():
                module_yaml = module_path / "module.yaml"
                if module_yaml.exists():
                    try:
                        info = ModuleInfo.from_yaml(str(module_yaml))
                        modules[info.name] = info
                    except Exception as e:
                        print(f"Warning: Failed to load module from {module_yaml}: {e}")
        return modules
    
    def load_module(self, name: str) -> bool:
        """Load a module by name."""
        modules = self.discover_modules()
        if name not in modules:
            return False
        
        info = modules[name]
        module_path = self.modules_dir / name
        
        module = Module(info=info, path=module_path)
        if module.load():
            self._modules[name] = module
            return True
        return False
    
    def unload_module(self, name: str) -> bool:
        """Unload a module by name."""
        if name not in self._modules:
            return False
        self._modules[name].unload()
        del self._modules[name]
        return True
    
    def is_module_enabled(self, name: str) -> bool:
        """Check if a module is enabled."""
        modules = self.discover_modules()
        if name not in modules:
            return False
        return modules[name].enabled
    
    def enable_module(self, name: str) -> bool:
        """Enable a module."""
        modules = self.discover_modules()
        if name not in modules:
            return False
        
        module_yaml = self.modules_dir / name / "module.yaml"
        with open(module_yaml, 'r') as f:
            data = yaml.safe_load(f)
        
        data["enabled"] = True
        with open(module_yaml, 'w') as f:
            yaml.dump(data, f)
        
        return True
    
    def disable_module(self, name: str) -> bool:
        """Disable a module."""
        modules = self.discover_modules()
        if name not in modules:
            return False
        
        module_yaml = self.modules_dir / name / "module.yaml"
        with open(module_yaml, 'r') as f:
            data = yaml.safe_load(f)
        
        data["enabled"] = False
        with open(module_yaml, 'w') as f:
            yaml.dump(data, f)
        
        if name in self._modules:
            self.unload_module(name)
        
        return True
    
    def list_modules(self) -> List[Dict[str, Any]]:
        """List all modules with their status."""
        all_modules = self.discover_modules()
        loaded = set(self._modules.keys())
        
        result = []
        for name, info in all_modules.items():
            result.append({
                "name": name,
                "version": info.version,
                "description": info.description,
                "author": info.author,
                "enabled": info.enabled,
                "loaded": name in loaded,
                "dependencies": info.dependencies,
                "permissions": info.permissions
            })
        return result
    
    def check_permissions(self, name: str, permission: str) -> bool:
        """Check if a module has a specific permission."""
        modules = self.discover_modules()
        if name not in modules:
            return False
        return permission in modules[name].permissions
    
    # Lifecycle hooks
    def run_hook(self, name: str, hook: str, *args, **kwargs) -> Any:
        """Run a lifecycle hook for a module."""
        if name not in self._hooks:
            self._hooks[name] = {}
        
        hook_func = self._hooks[name].get(hook)
        if hook_func:
            return hook_func(*args, **kwargs)
        return None
    
    def register_hook(self, name: str, hook: str, func: Any) -> None:
        """Register a lifecycle hook for a module."""
        if name not in self._hooks:
            self._hooks[name] = {}
        self._hooks[name][hook] = func


# Global module manager instance
_manager: Optional[ModuleManager] = None


def get_manager() -> ModuleManager:
    """Get the global module manager instance."""
    global _manager
    if _manager is None:
        _manager = ModuleManager()
    return _manager


def install_module(name: str, url: Optional[str] = None) -> bool:
    """Install a module from a URL or local path."""
    # TODO: Implement module installation from URL
    # For now, just load from local
    return get_manager().load_module(name)


def list_modules() -> List[Dict[str, Any]]:
    """List all modules."""
    return get_manager().list_modules()


def enable_module(name: str) -> bool:
    """Enable a module."""
    return get_manager().enable_module(name)


def disable_module(name: str) -> bool:
    """Disable a module."""
    return get_manager().disable_module(name)


def check_permission(module: str, permission: str) -> bool:
    """Check if a module has a permission."""
    return get_manager().check_permissions(module, permission)