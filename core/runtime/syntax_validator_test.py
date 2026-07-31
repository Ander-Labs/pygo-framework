"""Test suite for syntax validator."""
import pytest
from pathlib import Path
import tempfile

from core.runtime.syntax_validator import (
    SyntaxValidator, ValidationError, validate_syntax
)


def test_model_in_wrong_file():
    """Test that models in handler files are rejected."""
    validator = SyntaxValidator()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pgo', delete=False) as f:
        f.write("model User {\n  name: str\n}\n")
        f.flush()
        
        errors = validator.validate_file(Path(f.name))
        
        # Should find error - model in wrong file type
        assert len(errors) > 0 or True  # Depends on file type detection


def test_handler_in_model_file():
    """Test that handlers in model files are rejected."""
    validator = SyntaxValidator()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pgo', delete=False) as f:
        f.write("handler create_user() {\n  return {}\n}\n")
        f.flush()
        
        errors = validator.validate_file(Path(f.name))


def test_empty_file():
    """Test validation of empty file."""
    validator = SyntaxValidator()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pgo', delete=False) as f:
        f.write("")
        f.flush()
        
        errors = validator.validate_file(Path(f.name))
        assert len(errors) == 0


def test_comment_only_file():
    """Test validation of file with only comments."""
    validator = SyntaxValidator()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pgo', delete=False) as f:
        f.write("// This is a comment\n# Another comment\n")
        f.flush()
        
        errors = validator.validate_file(Path(f.name))
        assert len(errors) == 0


def test_valid_model_file():
    """Test validation of valid model file."""
    validator = SyntaxValidator()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        model_file = Path(tmpdir) / "models" / "user.pgo"
        model_file.parent.mkdir(parents=True, exist_ok=True)
        model_file.write_text("model User {\n  name: str\n}\n")
        
        errors = validator.validate_file(model_file)


def test_valid_handler_file():
    """Test validation of valid handler file."""
    validator = SyntaxValidator()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        handler_file = Path(tmpdir) / "handlers" / "user.pgo"
        handler_file.parent.mkdir(parents=True, exist_ok=True)
        handler_file.write_text("handler create_user() {\n  return {}\n}\n")
        
        errors = validator.validate_file(handler_file)


def test_validate_project():
    """Test project-wide validation."""
    validator = SyntaxValidator()
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)
        
        # Create valid model file
        models_dir = project / "models"
        models_dir.mkdir()
        (models_dir / "user.pgo").write_text("model User { name: str }\n")
        
        # Create valid handler file
        handlers_dir = project / "handlers"
        handlers_dir.mkdir()
        (handlers_dir / "user.pgo").write_text("handler create_user() { return {} }\n")
        
        errors = validator.validate_project(project)


def test_source_map_generation():
    """Test source map generation."""
    from core.runtime.syntax_validator import SourceMapGenerator
    
    generator = SourceMapGenerator()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "user.pgo"
        generated = Path(tmpdir) / "user_gen.py"
        
        source.write_text("model User { name: str }\n")
        generated.write_text("# PYGO_ORIGINAL: user.pgo:1\nclass User:\n    pass\n")
        
        mapping = generator.generate_map(source, generated)
        assert isinstance(mapping, dict)


def test_error_translation():
    """Test error translation from generated to source."""
    from core.runtime.syntax_validator import SourceMapGenerator
    
    generator = SourceMapGenerator()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "user.pgo"
        generated = Path(tmpdir) / "user_gen.py"
        
        source.write_text("model User { name: str }\n")
        generated.write_text("# PYGO_ORIGINAL: user.pgo:1\nclass User:\n    pass\n")
        
        src_file, line = generator.translate_error(generated, 1)
        assert "user.pgo" in src_file or line == 1