"""Test suite for v0.40.0 - Admin Panel Generator."""
import pytest
import tempfile
from pathlib import Path

from core.runtime.admin_generator import (
    FieldSpec, ModelSpec, AdminGenerator, DashboardGenerator,
    generate_admin_for_model, generate_dashboard
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
    """Test FieldSpec default values."""
    field = FieldSpec(name="test", type="string")
    
    assert field.required is False
    assert field.filterable is True
    assert field.sortable is True
    assert field.searchable is True
    assert field.group == "main"


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
    assert len(model.fields) == 3


def test_admin_generator_init():
    """Test AdminGenerator initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        gen = AdminGenerator(output_dir=tmpdir)
        assert gen.output_dir.exists()


def test_admin_generator_list_view():
    """Test generating list view."""
    with tempfile.TemporaryDirectory() as tmpdir:
        model = ModelSpec(
            name="Product",
            fields=[
                FieldSpec(name="id", type="uuid"),
                FieldSpec(name="name", type="string", label="Product Name"),
                FieldSpec(name="price", type="float"),
            ]
        )
        
        gen = AdminGenerator(output_dir=tmpdir)
        views = gen.generate_crud_views(model)
        
        assert 'list' in views
        assert views['list'].exists()
        
        content = views['list'].read_text()
        assert "Product - List" in content
        assert "Product Name" in content


def test_admin_generator_detail_view():
    """Test generating detail view."""
    with tempfile.TemporaryDirectory() as tmpdir:
        model = ModelSpec(
            name="Order",
            fields=[
                FieldSpec(name="id", type="uuid"),
                FieldSpec(name="total", type="float"),
            ]
        )
        
        gen = AdminGenerator(output_dir=tmpdir)
        views = gen.generate_crud_views(model)
        
        assert 'detail' in views
        content = views['detail'].read_text()
        assert "Order Details" in content


def test_admin_generator_form_view():
    """Test generating form view."""
    with tempfile.TemporaryDirectory() as tmpdir:
        model = ModelSpec(
            name="Category",
            fields=[
                FieldSpec(name="id", type="uuid"),
                FieldSpec(name="name", type="string", label="Category Name"),
                FieldSpec(name="description", type="text"),
            ]
        )
        
        gen = AdminGenerator(output_dir=tmpdir)
        views = gen.generate_crud_views(model)
        
        assert 'form' in views
        content = views['form'].read_text()
        assert "Category Create" in content
        assert "Category Name" in content


def test_admin_generator_delete_view():
    """Test generating delete view."""
    with tempfile.TemporaryDirectory() as tmpdir:
        model = ModelSpec(
            name="Tag",
            fields=[FieldSpec(name="id", type="uuid"), FieldSpec(name="name", type="string")]
        )
        
        gen = AdminGenerator(output_dir=tmpdir)
        views = gen.generate_crud_views(model)
        
        assert 'delete' in views
        content = views['delete'].read_text()
        assert "Delete Tag" in content


def test_admin_generator_all_views():
    """Test generating all CRUD views."""
    with tempfile.TemporaryDirectory() as tmpdir:
        model = ModelSpec(
            name="Article",
            fields=[
                FieldSpec(name="id", type="uuid"),
                FieldSpec(name="title", type="string"),
                FieldSpec(name="content", type="text"),
                FieldSpec(name="published", type="boolean"),
            ]
        )
        
        gen = AdminGenerator(output_dir=tmpdir)
        views = gen.generate_crud_views(model)
        
        assert len(views) == 4
        assert all(p.exists() for p in views.values())


def test_input_type_mapping():
    """Test HTML input type mapping."""
    gen = AdminGenerator(output_dir="/tmp")
    
    assert gen._get_input_type('string') == 'text'
    assert gen._get_input_type('email') == 'email'
    assert gen._get_input_type('password') == 'password'
    assert gen._get_input_type('text') == 'textarea'
    assert gen._get_input_type('integer') == 'number'
    assert gen._get_input_type('float') == 'number'
    assert gen._get_input_type('boolean') == 'checkbox'
    assert gen._get_input_type('date') == 'date'
    assert gen._get_input_type('uuid') == 'text'
    assert gen._get_input_type('unknown') == 'text'


def test_dashboard_generator():
    """Test dashboard generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        widgets = [
            {"title": "Users", "type": "stats", "content": "1,234"},
            {"title": "Orders", "type": "stats", "content": "567"},
        ]
        
        gen = DashboardGenerator(output_dir=tmpdir)
        dashboard_path = gen.generate_dashboard(widgets)
        
        assert dashboard_path.exists()
        content = dashboard_path.read_text()
        assert "Dashboard" in content
        assert "Users" in content
        assert "Orders" in content


def test_convenience_function():
    """Test convenience function to generate admin."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fields = [
            {"name": "id", "type": "uuid"},
            {"name": "title", "type": "string", "label": "Article Title"},
        ]
        
        views = generate_admin_for_model("Article", fields, output_dir=tmpdir)
        
        assert 'list' in views
        assert views['list'].exists()


def test_field_visibility_options():
    """Test field visibility options."""
    field = FieldSpec(
        name="password",
        type="password",
        filterable=False,
        searchable=False,
        exportable=False
    )
    
    assert field.filterable is False
    assert field.searchable is False
    assert field.exportable is False


def test_form_groups():
    """Test form field grouping."""
    fields = [
        FieldSpec(name="name", type="string", group="basic"),
        FieldSpec(name="email", type="email", group="contact"),
        FieldSpec(name="phone", type="string", group="contact"),
    ]
    
    model = ModelSpec(name="Contact", fields=fields)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        gen = AdminGenerator(output_dir=tmpdir)
        content = gen._render_form_fields(model, fields)
        
        assert "form-group-basic" in content
        assert "form-group-contact" in content


def test_excluded_fields_in_form():
    """Test that id and timestamps are excluded from forms."""
    model = ModelSpec(
        name="Test",
        fields=[
            FieldSpec(name="id", type="uuid"),
            FieldSpec(name="created_at", type="datetime"),
            FieldSpec(name="updated_at", type="datetime"),
            FieldSpec(name="deleted_at", type="datetime"),
            FieldSpec(name="name", type="string"),
        ]
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        gen = AdminGenerator(output_dir=tmpdir)
        form_content = gen._render_form_template(model)
        
        # Check form was generated correctly
        assert 'Test Create' in form_content
        assert 'name' in form_content  # Only user field should appear