"""Test suite for v0.41.0 - REST API Generator."""
import pytest
import tempfile
from pathlib import Path

from core.runtime.rest_generator import (
    FieldSpec, ModelSpec, RESTGenerator,
    generate_api_for_model
)


def test_field_spec_basic():
    """Test FieldSpec creation."""
    field = FieldSpec(name="email", type="email", label="Email Address")
    assert field.name == "email"
    assert field.type == "email"
    assert field.label == "Email Address"
    assert field.label_text == "Email Address"


def test_field_spec_label_text():
    """Test label_text property."""
    field = FieldSpec(name="user_name", type="string")
    assert field.label_text == "User Name"


def test_field_spec_defaults():
    """Test default values in FieldSpec."""
    field = FieldSpec(name="test", type="string")
    assert field.required is False
    assert field.filterable is True
    assert field.sortable is True
    assert field.searchable is True


def test_model_spec():
    """Test ModelSpec creation."""
    fields = [
        FieldSpec(name="id", type="uuid"),
        FieldSpec(name="name", type="string"),
        FieldSpec(name="email", type="email"),
    ]
    model = ModelSpec(name="User", fields=fields, plural_name="Users")
    assert model.name == "User"
    assert model.plural == "Users"
    assert model.routes_prefix == "/user"


def test_rest_generator_init():
    """Test RESTGenerator initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        gen = RESTGenerator(output_dir=tmpdir)
        assert gen.output_dir.exists()


def test_rest_generator_generate_api():
    """Test generating complete API."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fields = [
            {"name": "id", "type": "uuid"},
            {"name": "title", "type": "string", "label": "Title"},
            {"name": "content", "type": "text"},
            {"name": "published", "type": "boolean"},
        ]
        
        gen = RESTGenerator(output_dir=tmpdir)
        model = ModelSpec(name="Article", fields=[FieldSpec(**f) for f in fields])
        views = gen.generate_api_for_model(model)
        
        assert 'handler' in views
        assert 'go_handler' in views
        assert 'openapi' in views
        assert all(p.exists() for p in views.values())


def test_python_handler_content():
    """Test Python handler content generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        model = ModelSpec(
            name="Product",
            fields=[
                FieldSpec(name="id", type="uuid"),
                FieldSpec(name="name", type="string"),
            ]
        )
        
        gen = RESTGenerator(output_dir=tmpdir)
        handler_path = gen.output_dir / "product_handler.py"
        gen.write_handler(handler_path, model)
        
        content = handler_path.read_text()
        assert "def list_product" in content
        assert "def get_product" in content
        assert "def create_product" in content
        assert "def update_product" in content
        assert "def delete_product" in content
        assert "def bulk_create_product" in content
        assert "def bulk_delete_product" in content


def test_go_handler_content():
    """Test Go handler content generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        model = ModelSpec(name="Order", fields=[])
        
        gen = RESTGenerator(output_dir=tmpdir)
        go_handler_path = Path(tmpdir) / "order_handler.go"
        gen.write_go_handler(go_handler_path, model)
        
        content = go_handler_path.read_text()
        assert "func ListOrder" in content
        assert "func GetOrder" in content
        assert "func CreateOrder" in content
        assert "func UpdateOrder" in content
        assert "func DeleteOrder" in content


def test_openapi_spec_generation():
    """Test OpenAPI spec generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        model = ModelSpec(
            name="User",
            fields=[
                FieldSpec(name="id", type="uuid"),
                FieldSpec(name="email", type="email"),
            ],
            description="User model",
            plural_name="Users"
        )
        
        gen = RESTGenerator(output_dir=tmpdir)
        openapi_path = gen.output_dir / "user.openapi.json"
        gen.write_openapi_spec(openapi_path, model)
        
        content = openapi_path.read_text()
        assert '"openapi": "3.0.0"' in content
        assert '"title": "User API"' in content
        assert '"/users"' in content
        assert '"/users/{id}"' in content


def test_convenience_function():
    """Test convenience function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fields = [
            {"name": "id", "type": "uuid"},
            {"name": "title", "type": "string"},
        ]
        
        views = generate_api_for_model("Post", fields, output_dir=tmpdir)
        
        assert 'handler' in views
        assert views['handler'].exists()


def test_handler_includes_pagination():
    """Test that handler includes pagination."""
    with tempfile.TemporaryDirectory() as tmpdir:
        model = ModelSpec(name="Item", fields=[])
        
        gen = RESTGenerator(output_dir=tmpdir)
        handler_path = gen.output_dir / "item_handler.py"
        gen.write_handler(handler_path, model)
        
        content = handler_path.read_text()
        assert "pagination" in content
        assert "page" in content
        assert "per_page" in content


def test_handler_includes_filtering():
    """Test that handler includes filtering."""
    with tempfile.TemporaryDirectory() as tmpdir:
        model = ModelSpec(name="Tag", fields=[])
        
        gen = RESTGenerator(output_dir=tmpdir)
        handler_path = gen.output_dir / "tag_handler.py"
        gen.write_handler(handler_path, model)
        
        content = handler_path.read_text()
        assert "filters" in content
        assert "query.where" in content


def test_handler_includes_sorting():
    """Test that handler includes sorting."""
    with tempfile.TemporaryDirectory() as tmpdir:
        model = ModelSpec(name="Comment", fields=[])
        
        gen = RESTGenerator(output_dir=tmpdir)
        handler_path = gen.output_dir / "comment_handler.py"
        gen.write_handler(handler_path, model)
        
        content = handler_path.read_text()
        assert "sort" in content
        assert "order_by" in content


def test_handler_includes_fields_selection():
    """Test that handler includes field selection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        model = ModelSpec(name="Note", fields=[])
        
        gen = RESTGenerator(output_dir=tmpdir)
        handler_path = gen.output_dir / "note_handler.py"
        gen.write_handler(handler_path, model)
        
        content = handler_path.read_text()
        assert "fields" in content


def test_handler_includes_includes():
    """Test that handler includes relationship loading."""
    with tempfile.TemporaryDirectory() as tmpdir:
        model = ModelSpec(name="Invoice", fields=[])
        
        gen = RESTGenerator(output_dir=tmpdir)
        handler_path = gen.output_dir / "invoice_handler.py"
        gen.write_handler(handler_path, model)
        
        content = handler_path.read_text()
        assert "includes" in content


def test_handler_includes_bulk_operations():
    """Test that handler includes bulk operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        model = ModelSpec(name="Task", fields=[])
        
        gen = RESTGenerator(output_dir=tmpdir)
        handler_path = gen.output_dir / "task_handler.py"
        gen.write_handler(handler_path, model)
        
        content = handler_path.read_text()
        assert "bulk_create" in content
        assert "bulk_delete" in content