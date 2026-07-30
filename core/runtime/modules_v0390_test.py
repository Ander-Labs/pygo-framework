"""Test suite for v0.39.0 - Module System."""
import pytest
import tempfile
import os
from pathlib import Path

from core.runtime.modules import (
    ModuleManifest, Module, ModuleManager,
    get_module_manager, init_module_manager
)


def test_module_manifest_from_yaml():
    """Test loading manifest from YAML file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "module.yaml"
        manifest_path.write_text("""
module:
  name: test-module
  version: 1.0.0
  author: Test Author
  description: Test module

dependencies:
  modules:
    - core
  python_packages:
    - requests>=2.28.0

permissions:
  read:
    - user:read
  write:
    - user:write

hooks:
  on_install: hooks/install.py

ui:
  menu_items:
    - label: Test
      path: /test
""")
        
        manifest = ModuleManifest.from_yaml(str(manifest_path))
        
        assert manifest.name == "test-module"
        assert manifest.version == "1.0.0"
        assert manifest.author == "Test Author"
        assert manifest.dependencies["modules"] == ["core"]
        assert manifest.permissions["read"] == ["user:read"]
        assert manifest.hooks["on_install"] == "hooks/install.py"


def test_module_manifest_defaults():
    """Test default values in manifest."""
    manifest = ModuleManifest(name="test")
    
    assert manifest.version == "1.0.0"
    assert manifest.pygo_version == ">=1.0.0"
    assert manifest.license == "AGPL-3.0"
    assert manifest.dependencies == {}


def test_module_dataclass():
    """Test Module dataclass."""
    manifest = ModuleManifest(name="test-module")
    module = Module(manifest=manifest, path=Path("/tmp/test"))
    
    assert module.name == "test-module"
    assert module.routes_prefix == "/test-module"


def test_module_manager_list():
    """Test listing modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a module directory
        module_dir = Path(tmpdir) / "test-module"
        module_dir.mkdir()
        
        # Create module.yaml
        manifest_path = module_dir / "module.yaml"
        manifest_path.write_text("""
module:
  name: test-module
  version: 1.0.0
""")
        
        manager = ModuleManager(modules_dir=tmpdir)
        modules = manager.list_modules()
        
        assert len(modules) == 1
        assert modules[0].name == "test-module"


def test_module_manager_get():
    """Test getting a module by name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        module_dir = Path(tmpdir) / "test-module"
        module_dir.mkdir()
        
        manifest_path = module_dir / "module.yaml"
        manifest_path.write_text("""
module:
  name: test-module
  version: 1.0.0
""")
        
        manager = ModuleManager(modules_dir=tmpdir)
        module = manager.get_module("test-module")
        
        assert module is not None
        assert module.name == "test-module"


def test_module_manager_enable_disable():
    """Test enabling and disabling modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        module_dir = Path(tmpdir) / "test-module"
        module_dir.mkdir()
        
        manifest_path = module_dir / "module.yaml"
        manifest_path.write_text("""
module:
  name: test-module
  version: 1.0.0
""")
        
        manager = ModuleManager(modules_dir=tmpdir)
        
        # Initially disabled
        module = manager.get_module("test-module")
        assert module is not None
        assert not module.is_enabled
        
        # Enable
        manager.enable("test-module")
        module = manager.get_module("test-module")
        assert module.is_enabled
        assert (module_dir / ".enabled").exists()
        
        # Disable
        manager.disable("test-module")
        module = manager.get_module("test-module")
        assert not module.is_enabled
        assert not (module_dir / ".enabled").exists()


def test_module_manager_install():
    """Test installing a module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create source module with matching name
        source_dir = Path(tmpdir) / "my-module"
        source_dir.mkdir()
        
        manifest_path = source_dir / "module.yaml"
        manifest_path.write_text("""
module:
  name: my-module
  version: 1.0.0
""")
        
        # Set modules directory
        modules_dir = Path(tmpdir) / "modules"
        modules_dir.mkdir()
        
        manager = ModuleManager(modules_dir=str(modules_dir))
        
        # Install with same name
        result = manager.install(str(source_dir), name="my-module")
        assert result is True
        
        # Check module is loaded
        installed = manager.get_module("my-module")
        assert installed is not None
        assert (modules_dir / "my-module").exists()


def test_module_manager_get_routes():
    """Test getting routes from enabled modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        module_dir = Path(tmpdir) / "test-module"
        module_dir.mkdir()
        
        manifest_path = module_dir / "module.yaml"
        manifest_path.write_text("""
module:
  name: test-module
  version: 1.0.0

routes:
  prefix: /test
  auto_generate: true
""")
        
        manager = ModuleManager(modules_dir=tmpdir)
        
        # Initially no enabled modules
        routes = manager.get_routes()
        assert len(routes) == 0
        
        # Enable module
        manager.enable("test-module")
        
        # Check routes
        routes = manager.get_routes()
        assert "/test" in routes
        assert routes["/test"]["module"] == "test-module"


def test_module_manager_get_models():
    """Test getting models from enabled modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        module_dir = Path(tmpdir) / "test-module"
        module_dir.mkdir()
        
        # Create models directory
        models_dir = module_dir / "models"
        models_dir.mkdir()
        
        # Create model file
        model_file = models_dir / "user.pgo"
        model_file.write_text("model User:\n  email: Email")
        
        manifest_path = module_dir / "module.yaml"
        manifest_path.write_text("""
module:
  name: test-module
  version: 1.0.0

models:
  path: models/
  pattern: "*.pgo"
""")
        
        manager = ModuleManager(modules_dir=tmpdir)
        
        # Enable module
        manager.enable("test-module")
        
        # Get models
        models = manager.get_models()
        assert "user.pgo" in models


def test_module_manager_uninstall():
    """Test uninstalling a module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        module_dir = Path(tmpdir) / "test-module"
        module_dir.mkdir()
        
        manifest_path = module_dir / "module.yaml"
        manifest_path.write_text("""
module:
  name: test-module
  version: 1.0.0
""")
        
        manager = ModuleManager(modules_dir=tmpdir)
        
        # Verify module exists
        assert manager.get_module("test-module") is not None
        
        # Uninstall
        manager.uninstall("test-module")
        
        # Verify module is gone
        assert manager.get_module("test-module") is None
        assert not module_dir.exists()


def test_module_manager_run_hook():
    """Test running lifecycle hooks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        module_dir = Path(tmpdir) / "test-module"
        module_dir.mkdir()
        
        hooks_dir = module_dir / "hooks"
        hooks_dir.mkdir()
        
        # Create hooks directory
        manifest_path = module_dir / "module.yaml"
        manifest_path.write_text("""
module:
  name: test-module
  version: 1.0.0

hooks:
  on_install: hooks/install.py
  on_enable: hooks/enable.py
""")
        
        # Create install hook
        install_hook = hooks_dir / "install.py"
        install_hook.write_text("""
# Install hook
import os
with open('installed.txt', 'w') as f:
    f.write('installed')
""")
        
        # Create enable hook
        enable_hook = hooks_dir / "enable.py"
        enable_hook.write_text("""
# Enable hook
import os
with open('enabled.txt', 'w') as f:
    f.write('enabled')
""")
        
        manager = ModuleManager(modules_dir=tmpdir)
        
        # Run install hook
        manager._run_hook("test-module", "on_install")
        assert (module_dir / "installed.txt").exists()
        
        # Run enable hook
        manager._run_hook("test-module", "on_enable")
        assert (module_dir / "enabled.txt").exists()


def test_global_module_manager():
    """Test global module manager singleton."""
    # Reset
    import core.runtime.modules as modules
    modules._module_manager = None
    
    manager1 = get_module_manager()
    manager2 = get_module_manager()
    
    assert manager1 is manager2


def test_init_module_manager():
    """Test initializing module manager with custom path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = init_module_manager(tmpdir)
        
        assert manager.modules_dir == Path(tmpdir)


def test_module_not_found():
    """Test error when module not found."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ModuleManager(modules_dir=tmpdir)
        
        with pytest.raises(ValueError, match="not found"):
            manager.enable("nonexistent")


def test_module_already_exists():
    """Test error when installing duplicate module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        module_dir = Path(tmpdir) / "existing-module"
        module_dir.mkdir()
        
        manifest_path = module_dir / "module.yaml"
        manifest_path.write_text("""
module:
  name: existing-module
  version: 1.0.0
""")
        
        manager = ModuleManager(modules_dir=tmpdir)
        
        with pytest.raises(FileExistsError):
            manager.install(str(module_dir), name="existing-module")
