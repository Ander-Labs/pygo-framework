"""Test suite for v0.29.0 - Module System."""
import pytest
import tempfile
import os
import yaml
from pathlib import Path

from core.runtime.modules import (
    ModuleInfo, Module, ModuleManager,
    get_manager, install_module, list_modules,
    enable_module, disable_module, check_permission
)


def test_v0290_module_info_from_yaml():
    """Test loading module info from YAML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        module_yaml = Path(tmpdir) / "module.yaml"
        data = {
            "name": "test_module",
            "version": "1.0.0",
            "description": "Test module",
            "author": "Test Author",
            "entry": "app.py",
            "dependencies": ["core"],
            "permissions": ["read", "write"],
            "enabled": True
        }
        
        with open(module_yaml, 'w') as f:
            yaml.dump(data, f)
        
        info = ModuleInfo.from_yaml(str(module_yaml))
        
        assert info.name == "test_module"
        assert info.version == "1.0.0"
        assert info.description == "Test module"
        assert info.author == "Test Author"
        assert info.entry == "app.py"
        assert info.dependencies == ["core"]
        assert info.permissions == ["read", "write"]
        assert info.enabled is True


def test_v0290_module_manager_discover():
    """Test module discovery."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test module
        module_dir = Path(tmpdir) / "test_module"
        module_dir.mkdir()
        
        module_yaml = module_dir / "module.yaml"
        with open(module_yaml, 'w') as f:
            yaml.dump({"name": "test_module", "version": "1.0.0"}, f)
        
        # Create empty app.py
        (module_dir / "app.py").write_text("# empty")
        
        mm = ModuleManager(modules_dir=tmpdir)
        modules = mm.discover_modules()
        
        assert "test_module" in modules
        assert modules["test_module"].version == "1.0.0"


def test_v0290_module_enable_disable():
    """Test enabling and disabling modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        module_dir = Path(tmpdir) / "test_module"
        module_dir.mkdir()
        
        module_yaml = module_dir / "module.yaml"
        with open(module_yaml, 'w') as f:
            yaml.dump({"name": "test_module", "version": "1.0.0", "enabled": False}, f)
        
        mm = ModuleManager(modules_dir=tmpdir)
        
        # Initially disabled
        assert not mm.is_module_enabled("test_module")
        
        # Enable
        mm.enable_module("test_module")
        assert mm.is_module_enabled("test_module")
        
        # Disable
        mm.disable_module("test_module")
        assert not mm.is_module_enabled("test_module")


def test_v0290_module_list():
    """Test listing modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create two test modules
        for i in range(2):
            module_dir = Path(tmpdir) / f"module_{i}"
            module_dir.mkdir()
            module_yaml = module_dir / "module.yaml"
            with open(module_yaml, 'w') as f:
                yaml.dump({
                    "name": f"module_{i}",
                    "version": "1.0.0",
                    "enabled": True
                }, f)
        
        mm = ModuleManager(modules_dir=tmpdir)
        modules = mm.list_modules()
        
        assert len(modules) == 2
        names = [m["name"] for m in modules]
        assert "module_0" in names
        assert "module_1" in names


def test_v0290_module_permissions():
    """Test module permission checking."""
    with tempfile.TemporaryDirectory() as tmpdir:
        module_dir = Path(tmpdir) / "test_module"
        module_dir.mkdir()
        
        module_yaml = module_dir / "module.yaml"
        with open(module_yaml, 'w') as f:
            yaml.dump({
                "name": "test_module",
                "version": "1.0.0",
                "permissions": ["read", "write"]
            }, f)
        
        mm = ModuleManager(modules_dir=tmpdir)
        
        assert mm.check_permissions("test_module", "read")
        assert mm.check_permissions("test_module", "write")
        assert not mm.check_permissions("test_module", "delete")


def test_v0290_module_lifecycle_hooks():
    """Test module lifecycle hooks."""
    mm = ModuleManager()
    
    # Register hooks
    mm.register_hook("test_module", "on_install", lambda: "installed")
    mm.register_hook("test_module", "on_enable", lambda: "enabled")
    
    assert mm.run_hook("test_module", "on_install") == "installed"
    assert mm.run_hook("test_module", "on_enable") == "enabled"


def test_v0290_convenience_functions():
    """Test convenience functions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Set up a module
        module_dir = Path(tmpdir) / "test_module"
        module_dir.mkdir()
        module_yaml = module_dir / "module.yaml"
        with open(module_yaml, 'w') as f:
            yaml.dump({"name": "test_module", "version": "1.0.0"}, f)
        
        # Override manager for test
        from core.runtime import modules
        modules._manager = ModuleManager(modules_dir=tmpdir)
        
        # Test list_modules
        modules_list = list_modules()
        assert len(modules_list) == 1
        assert modules_list[0]["name"] == "test_module"
        
        # Test enable/disable
        assert enable_module("test_module")
        assert disable_module("test_module")
        
        # Test permission check
        assert check_permission("test_module", "read") is False  # No perms defined


def test_v0290_module_load_unload():
    """Test loading and unloading modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        module_dir = Path(tmpdir) / "test_module"
        module_dir.mkdir()
        
        module_yaml = module_dir / "module.yaml"
        with open(module_yaml, 'w') as f:
            yaml.dump({"name": "test_module", "version": "1.0.0"}, f)
        
        # Create a simple app.py
        app_py = module_dir / "app.py"
        app_py.write_text("HANDLER = 'test_handler'")
        
        mm = ModuleManager(modules_dir=tmpdir)
        
        # Load module
        assert mm.load_module("test_module")
        assert "test_module" in mm._modules
        
        # Unload module
        assert mm.unload_module("test_module")
        assert "test_module" not in mm._modules