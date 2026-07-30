"""PyGo Module System (v0.39.0).

Provides module management, loading, and lifecycle hooks.
"""

from __future__ import annotations

import os
import yaml
import importlib.util
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from contextlib import contextmanager

import sys


@dataclass
class ModuleManifest:
    """Module manifest parsed from module.yaml."""
    name: str
    version: str = "1.0.0"
    pygo_version: str = ">=1.0.0"
    author: str = ""
    description: str = ""
    license: str = "AGPL-3.0"
    homepage: str = ""
    repository: str = ""
    
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    permissions: Dict[str, List[str]] = field(default_factory=dict)
    hooks: Dict[str, str] = field(default_factory=dict)
    ui: Dict[str, Any] = field(default_factory=dict)
    routes: Dict[str, Any] = field(default_factory=dict)
    models: Dict[str, Any] = field(default_factory=dict)
    views: Dict[str, Any] = field(default_factory=dict)
    assets: Dict[str, Any] = field(default_factory=dict)
    migrations: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, path: str) -> "ModuleManifest":
        """Load manifest from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        
        module = data.get("module", {})
        return cls(
            name=module.get("name", "unknown"),
            version=module.get("version", "1.0.0"),
            pygo_version=module.get("pygo_version", ">=1.0.0"),
            author=module.get("author", ""),
            description=module.get("description", ""),
            license=module.get("license", "AGPL-3.0"),
            homepage=module.get("homepage", ""),
            repository=module.get("repository", ""),
            dependencies=data.get("dependencies", {"modules": [], "python_packages": []}),
            permissions=data.get("permissions", {}),
            hooks=data.get("hooks", {}),
            ui=data.get("ui", {}),
            routes=data.get("routes", {}),
            models=data.get("models", {}),
            views=data.get("views", {}),
            assets=data.get("assets", {}),
            migrations=data.get("migrations", {}),
        )


@dataclass
class Module:
    """Loaded PyGo module."""
    manifest: ModuleManifest
    path: Path
    is_enabled: bool = False
    
    @property
    def name(self) -> str:
        return self.manifest.name
    
    @property
    def routes_prefix(self) -> str:
        return self.manifest.routes.get("prefix", f"/{self.name}")


class ModuleManager:
    """Manages PyGo modules: install, enable, disable, list."""
    
    MODULES_DIR = Path("modules")
    
    def __init__(self, modules_dir: Optional[str] = None):
        self.modules_dir = Path(modules_dir) if modules_dir else self.MODULES_DIR
        self._modules: Dict[str, Module] = {}
        self._load_modules()
    
    def _load_modules(self) -> None:
        """Load all modules from the modules directory."""
        if not self.modules_dir.exists():
            self.modules_dir.mkdir(parents=True, exist_ok=True)
            return
        
        for module_dir in self.modules_dir.iterdir():
            if module_dir.is_dir():
                manifest_path = module_dir / "module.yaml"
                if manifest_path.exists():
                    try:
                        manifest = ModuleManifest.from_yaml(str(manifest_path))
                        self._modules[manifest.name] = Module(
                            manifest=manifest,
                            path=module_dir,
                            is_enabled=(module_dir / ".enabled").exists()
                        )
                    except Exception as e:
                        print(f"Warning: Failed to load module from {module_dir}: {e}")
    
    def list_modules(self) -> List[Module]:
        """List all available modules."""
        return list(self._modules.values())
    
    def get_module(self, name: str) -> Optional[Module]:
        """Get a module by name."""
        return self._modules.get(name)
    
    def install(self, source: str, name: Optional[str] = None) -> bool:
        """Install a module from a source (path, git URL, or package)."""
        source_path = Path(source)
        
        if not source_path.exists():
            # Could be a git URL or package name
            raise NotImplementedError("Git/package installation not yet implemented")
        
        module_name = name or source_path.name
        dest_path = self.modules_dir / module_name
        
        if dest_path.exists():
            raise FileExistsError(f"Module {module_name} already exists")
        
        # Copy module directory
        import shutil
        shutil.copytree(source_path, dest_path)
        
        # Run install hook
        self._run_hook(module_name, "on_install")
        
        # Reload modules
        self._load_modules()
        return True
    
    def enable(self, name: str) -> bool:
        """Enable a module."""
        module = self.get_module(name)
        if not module:
            raise ValueError(f"Module {name} not found")
        
        if not module.is_enabled:
            # Create .enabled marker file
            (module.path / ".enabled").touch()
            module.is_enabled = True
            self._run_hook(name, "on_enable")
        
        return True
    
    def disable(self, name: str) -> bool:
        """Disable a module."""
        module = self.get_module(name)
        if not module:
            raise ValueError(f"Module {name} not found")
        
        if module.is_enabled:
            # Remove .enabled marker file
            enabled_file = module.path / ".enabled"
            if enabled_file.exists():
                enabled_file.unlink()
            module.is_enabled = False
            self._run_hook(name, "on_disable")
        
        return True
    
    def uninstall(self, name: str) -> bool:
        """Uninstall a module."""
        module = self.get_module(name)
        if not module:
            raise ValueError(f"Module {name} not found")
        
        # Run uninstall hook
        self._run_hook(name, "on_uninstall")
        
        # Remove module directory
        import shutil
        shutil.rmtree(module.path)
        
        # Remove from loaded modules
        del self._modules[name]
        return True
    
    def _run_hook(self, module_name: str, hook_name: str) -> bool:
        """Run a lifecycle hook for a module."""
        module = self.get_module(module_name)
        if not module:
            return False
        
        hook_path = module.manifest.hooks.get(hook_name)
        if not hook_path:
            return True  # No hook defined
        
        hook_file = module.path / hook_path
        if not hook_file.exists():
            return True  # Hook file doesn't exist
        
        try:
            # Execute hook as Python script
            with open(hook_file) as f:
                code = f.read()
            
            # Save current directory and change to module directory
            old_cwd = os.getcwd()
            os.chdir(module.path)
            
            try:
                # Execute in module context
                namespace = {"module": module, "manifest": module.manifest, "os": os}
                exec(code, namespace)
                return True
            finally:
                os.chdir(old_cwd)
        except Exception as e:
            print(f"Warning: Hook {hook_name} failed for module {module_name}: {e}")
            return False
    
    def get_routes(self) -> Dict[str, Any]:
        """Get all routes from enabled modules."""
        routes = {}
        for module in self.list_modules():
            if module.is_enabled:
                prefix = module.routes_prefix
                routes[prefix] = {
                    "module": module.name,
                    "auto_generate": module.manifest.routes.get("auto_generate", False)
                }
        return routes
    
    def get_models(self) -> Dict[str, Path]:
        """Get all model files from enabled modules."""
        models = {}
        for module in self.list_modules():
            if module.is_enabled:
                models_path = module.path / module.manifest.models.get("path", "models/")
                if models_path.exists():
                    for model_file in models_path.glob(module.manifest.models.get("pattern", "*.pgo")):
                        models[model_file.name] = model_file
        return models


# Global module manager instance
_module_manager: Optional[ModuleManager] = None


def get_module_manager() -> ModuleManager:
    """Get the global module manager instance."""
    global _module_manager
    if _module_manager is None:
        _module_manager = ModuleManager()
    return _module_manager


def init_module_manager(modules_dir: Optional[str] = None) -> ModuleManager:
    """Initialize the module manager with custom modules directory."""
    global _module_manager
    _module_manager = ModuleManager(modules_dir)
    return _module_manager
