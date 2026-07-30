"""Test suite for v0.30.0 - Admin Panel and API REST."""
import pytest
import json

from core.runtime.admin import (
    ModelField, Model, AdminGenerator,
    generate_api, generate_routes
)


def test_v0300_model_field():
    """Test ModelField dataclass."""
    field = ModelField(
        name="email",
        type="email",
        required=True,
        unique=True,
        description="User email address"
    )
    
    assert field.name == "email"
    assert field.type == "email"
    assert field.required is True
    assert field.unique is True
    assert field.description == "User email address"


def test_v0300_model():
    """Test Model dataclass."""
    model = Model(
        name="User",
        fields=[
            ModelField(name="id", type="uuid"),
            ModelField(name="email", type="email")
        ]
    )
    
    assert model.name == "User"
    assert len(model.fields) == 2
    assert model.table == "user"  # Auto-generated


def test_v0300_model_custom_table():
    """Test Model with custom table name."""
    model = Model(
        name="User",
        fields=[],
        table="users"
    )
    
    assert model.table == "users"


def test_v0300_admin_generator_crud_routes():
    """Test CRUD route generation."""
    models = {
        "User": Model(
            name="User",
            fields=[
                ModelField(name="id", type="uuid"),
                ModelField(name="email", type="email")
            ]
        ),
        "Product": Model(
            name="Product",
            fields=[
                ModelField(name="id", type="uuid"),
                ModelField(name="name", type="string")
            ]
        )
    }
    
    gen = AdminGenerator(models)
    routes = gen.generate_crud_routes()
    
    assert "User" in routes
    assert "Product" in routes
    
    # Check User routes
    user_routes = routes["User"]
    assert len(user_routes) == 5  # CRUD + list
    
    methods = [r["method"] for r in user_routes]
    assert "GET" in methods
    assert "POST" in methods
    assert "PUT" in methods
    assert "DELETE" in methods


def test_v0300_openapi_spec():
    """Test OpenAPI spec generation."""
    models = {
        "User": Model(
            name="User",
            fields=[
                ModelField(name="id", type="uuid", description="User ID"),
                ModelField(name="email", type="email", description="Email"),
                ModelField(name="name", type="string", description="Name")
            ]
        )
    }
    
    gen = AdminGenerator(models)
    spec = gen.generate_openapi_spec(title="Test API", version="1.0.0")
    
    assert spec["openapi"] == "3.0.0"
    assert spec["info"]["title"] == "Test API"
    assert spec["info"]["version"] == "1.0.0"
    
    # Check schema
    assert "User" in spec["components"]["schemas"]
    user_schema = spec["components"]["schemas"]["User"]
    assert user_schema["type"] == "object"
    assert "id" in user_schema["properties"]
    assert "email" in user_schema["properties"]
    
    # Check paths
    assert "/user" in spec["paths"]
    assert "/user/{id}" in spec["paths"]


def test_v0300_openapi_type_mapping():
    """Test OpenAPI type mapping."""
    gen = AdminGenerator({})
    
    assert gen._map_type_to_openapi("string") == "string"
    assert gen._map_type_to_openapi("int") == "integer"
    assert gen._map_type_to_openapi("float") == "number"
    assert gen._map_type_to_openapi("bool") == "boolean"
    assert gen._map_type_to_openapi("uuid") == "string"
    assert gen._map_type_to_openapi("array") == "array"


def test_v0300_openapi_filter_parameters():
    """Test OpenAPI filter parameters."""
    models = {
        "User": Model(
            name="User",
            fields=[
                ModelField(name="id", type="uuid"),
                ModelField(name="email", type="email")
            ]
        )
    }
    
    gen = AdminGenerator(models)
    spec = gen.generate_openapi_spec()
    
    get_path = spec["paths"]["/user"]["get"]
    params = get_path["parameters"]
    
    param_names = [p["name"] for p in params]
    assert "limit" in param_names
    assert "offset" in param_names
    assert "filter" in param_names


def test_v0300_convenience_functions():
    """Test convenience functions."""
    models = {
        "User": Model(
            name="User",
            fields=[
                ModelField(name="id", type="uuid"),
                ModelField(name="email", type="email")
            ]
        )
    }
    
    # Test generate_api
    spec = generate_api(models, title="Test API")
    assert spec["openapi"] == "3.0.0"
    
    # Test generate_routes
    routes = generate_routes(models)
    assert "User" in routes


def test_v0300_multiple_models():
    """Test with multiple models."""
    models = {
        "Customer": Model(
            name="Customer",
            fields=[
                ModelField(name="id", type="uuid"),
                ModelField(name="name", type="string"),
                ModelField(name="email", type="email")
            ]
        ),
        "Order": Model(
            name="Order",
            fields=[
                ModelField(name="id", type="uuid"),
                ModelField(name="customer_id", type="uuid"),
                ModelField(name="total", type="decimal")
            ]
        ),
        "Product": Model(
            name="Product",
            fields=[
                ModelField(name="id", type="uuid"),
                ModelField(name="name", type="string"),
                ModelField(name="price", type="decimal")
            ]
        )
    }
    
    gen = AdminGenerator(models)
    spec = gen.generate_openapi_spec()
    
    # All models should be in schemas
    assert "Customer" in spec["components"]["schemas"]
    assert "Order" in spec["components"]["schemas"]
    assert "Product" in spec["components"]["schemas"]
    
    # All models should have routes
    routes = gen.generate_crud_routes()
    assert "Customer" in routes
    assert "Order" in routes
    assert "Product" in routes