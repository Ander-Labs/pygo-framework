"""Test suite for v0.31.0 - Reports, Jobs, Email, Cache."""
import pytest
import tempfile
import os
from io import BytesIO

from core.runtime.reports import (
    ReportColumn, ReportDefinition, ReportEngine, ReportBuilder,
    generate_report, create_report
)


def test_v0310_report_column():
    """Test ReportColumn dataclass."""
    col = ReportColumn(
        name="email",
        label="Email Address",
        format="email",
        width=200
    )
    
    assert col.name == "email"
    assert col.label == "Email Address"
    assert col.format == "email"
    assert col.width == 200


def test_v0310_report_definition():
    """Test ReportDefinition creation."""
    col = ReportColumn(name="id", label="ID")
    defn = ReportDefinition(
        name="user_report",
        title="User Report",
        columns=[col],
        description="Report of all users"
    )
    
    assert defn.name == "user_report"
    assert defn.title == "User Report"
    assert len(defn.columns) == 1


def test_v0310_report_definition_from_dict():
    """Test ReportDefinition from dict."""
    data = {
        "name": "test_report",
        "title": "Test Report",
        "columns": [
            {"name": "id", "label": "ID"},
            {"name": "name", "label": "Name", "format": "string"}
        ]
    }
    
    defn = ReportDefinition.from_dict(data)
    assert defn.name == "test_report"
    assert len(defn.columns) == 2


def test_v0310_report_engine_csv():
    """Test CSV export."""
    data = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"}
    ]
    
    engine = ReportEngine(data)
    csv = engine.to_csv()
    
    assert "id,name" in csv
    assert "Alice" in csv
    assert "Bob" in csv


def test_v0310_report_engine_json():
    """Test JSON export."""
    data = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"}
    ]
    
    engine = ReportEngine(data)
    json_str = engine.to_json()
    
    assert '"id": 1' in json_str
    assert '"name": "Alice"' in json_str


def test_v0310_report_engine_empty():
    """Test empty data."""
    engine = ReportEngine([])
    
    assert engine.to_csv() == ""
    assert engine.to_json() == "[]"


def test_v0310_report_builder():
    """Test ReportBuilder with filters."""
    data = [
        {"id": 1, "name": "Alice", "status": "active"},
        {"id": 2, "name": "Bob", "status": "inactive"},
        {"id": 3, "name": "Charlie", "status": "active"}
    ]
    
    defn = create_report("users", "User Report", [{"name": "id", "label": "ID"}])
    builder = ReportBuilder(defn)
    
    # Filter active users
    engine = builder.filter("status", "eq", "active").build(data)
    csv = engine.to_csv()
    
    assert "Alice" in csv
    assert "Bob" not in csv
    assert "Charlie" in csv


def test_v0310_report_builder_sort():
    """Test ReportBuilder with sorting."""
    data = [
        {"id": 3, "name": "Charlie"},
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"}
    ]
    
    defn = create_report("users", "User Report", [{"name": "id", "label": "ID"}])
    builder = ReportBuilder(defn)
    
    # Sort by name
    engine = builder.sort("name").build(data)
    json_str = engine.to_json()
    
    # Should be sorted alphabetically
    assert json_str.index("Alice") < json_str.index("Bob") < json_str.index("Charlie")


def test_v0310_generate_report():
    """Test generate_report convenience function."""
    data = [{"id": 1, "name": "Test"}]
    
    csv = generate_report(data, "csv")
    assert "id,name" in csv
    
    json_str = generate_report(data, "json")
    assert '"id": 1' in json_str


def test_v0310_excel_export():
    """Test Excel export (requires openpyxl)."""
    try:
        import openpyxl
        data = [{"id": 1, "name": "Test"}]
        
        engine = ReportEngine(data)
        excel = engine.to_excel()
        
        assert isinstance(excel, BytesIO)
    except ImportError:
        pytest.skip("openpyxl not installed")


def test_v0310_pdf_export():
    """Test PDF export (requires reportlab)."""
    try:
        import reportlab
        data = [{"id": 1, "name": "Test"}]
        
        engine = ReportEngine(data)
        pdf = engine.to_pdf("Test Report")
        
        assert isinstance(pdf, bytes)
        assert len(pdf) > 0
    except ImportError:
        pytest.skip("reportlab not installed")