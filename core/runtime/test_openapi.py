"""Test suite for OpenAPI specification generation (v0.23.0)."""
import pytest
import json
from core.runtime.openapi import generate_openapi_spec


def test_openapi_basic():
    """Test basic OpenAPI spec generation."""
    models = [
        {"name": "User", "fields": [
            {"name": "id", "type": "UUID"},
            {"name": "email", "type": "Email"},
            {"name": "name", "type": "String"},
        ]}
    ]
    routes = [
        {"method": "GET", "path": "/users", "handler": "crud_user_list"},
        {"method": "GET", "path": "/users/:id", "handler": "crud_user_get"},
    ]
    
    spec = generate_openapi_spec(models, routes)
    
    # Verify openapi version
    assert spec["openapi"] == "3.0.3"
    
    # Verify info section
    assert spec["info"]["title"] == "PyGo API"
    assert spec["info"]["version"] == "1.0.0"
    
    # Verify model schema
    assert "User" in spec["components"]["schemas"]
    user_schema = spec["components"]["schemas"]["User"]
    assert user_schema["type"] == "object"
    assert "id" in user_schema["properties"]
    assert "email" in user_schema["properties"]
    
    # Verify routes
    assert "/users" in spec["paths"]
    assert "get" in spec["paths"]["/users"]
    assert "/users/{id}" in spec["paths"]
    
    # Verify path parameter
    path_spec = spec["paths"]["/users/{id}"]["get"]
    assert len(path_spec["parameters"]) == 1
    assert path_spec["parameters"][0]["name"] == "id"


def test_openapi_with_types():
    """Test OpenAPI spec with various types."""
    models = [
        {"name": "Product", "fields": [
            {"name": "id", "type": "UUID"},
            {"name": "name", "type": "String"},
            {"name": "price", "type": "Float"},
            {"name": "in_stock", "type": "Bool"},
            {"name": "created_at", "type": "DateTime"},
        ]}
    ]
    routes = [
        {"method": "POST", "path": "/products", "handler": "crud_product_create"},
        {"method": "DELETE", "path": "/products/:id", "handler": "crud_product_delete"},
    ]
    
    spec = generate_openapi_spec(models, routes)
    
    # Verify type mappings
    product = spec["components"]["schemas"]["Product"]
    assert product["properties"]["id"]["format"] == "uuid"
    assert product["properties"]["price"]["type"] == "number"
    assert product["properties"]["in_stock"]["type"] == "boolean"
    assert product["properties"]["created_at"]["format"] == "date-time"
    
    # Verify POST response
    post_spec = spec["paths"]["/products"]["post"]
    assert "201" in post_spec["responses"]
    
    # Verify DELETE response
    delete_spec = spec["paths"]["/products/{id}"]["delete"]
    assert "204" in delete_spec["responses"]


def test_openapi_json_export():
    """Test that spec can be exported as JSON."""
    models = [{"name": "Test", "fields": [{"name": "id", "type": "UUID"}]}]
    routes = [{"method": "GET", "path": "/test", "handler": "test_handler"}]
    
    spec = generate_openapi_spec(models, routes)
    
    # Should be JSON serializable
    json_str = json.dumps(spec, indent=2)
    assert '"openapi": "3.0.3"' in json_str
    
    # Should round-trip
    parsed = json.loads(json_str)
    assert parsed == spec