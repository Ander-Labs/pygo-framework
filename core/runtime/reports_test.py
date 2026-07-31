"""Test suite for v0.45.0 - Reports PDF/Excel."""
import pytest
from pathlib import Path
from datetime import datetime

from core.runtime.reports import (
    ReportConfig, ExcelColumn, ExcelConfig, ReportGenerator, ReportScheduler,
    generate_report, generate_pdf_report, generate_excel_report, generate_csv_report
)


def test_report_config_creation():
    """Test creating report config."""
    config = ReportConfig(title="Test Report", format="pdf")
    
    assert config.title == "Test Report"
    assert config.format == "pdf"
    assert config.page_size == "A4"


def test_report_config_defaults():
    """Test report config defaults."""
    config = ReportConfig(title="Test")
    
    assert config.format == "pdf"
    assert config.orientation == "portrait"
    assert config.margins == {"top": 1, "bottom": 1, "left": 1, "right": 1}


def test_excel_column_creation():
    """Test creating Excel column."""
    col = ExcelColumn(header="Name", field="name", width=100, format="text")
    
    assert col.header == "Name"
    assert col.field == "name"
    assert col.width == 100


def test_excel_config_creation():
    """Test creating Excel config."""
    config = ExcelConfig(
        columns=[
            ExcelColumn(header="ID", field="id"),
            ExcelColumn(header="Name", field="name")
        ]
    )
    
    assert len(config.columns) == 2
    assert config.frozen_rows == 1


def test_report_generator_init():
    """Test report generator initialization."""
    generator = ReportGenerator()
    
    assert generator.templates_dir.exists()
    assert generator.output_dir.exists()


def test_generate_pdf_report():
    """Test PDF report generation."""
    data = [
        {"Name": "John", "Age": 30},
        {"Name": "Jane", "Age": 25}
    ]
    
    path = generate_pdf_report(data, title="Test Report")
    
    assert path.exists()
    assert path.suffix == ".pdf"
    
    content = path.read_text()
    assert "Test Report" in content
    assert "John" in content
    
    # Cleanup
    path.unlink()


def test_generate_excel_report():
    """Test Excel report generation."""
    data = [
        {"Name": "John", "Age": 30},
        {"Name": "Jane", "Age": 25}
    ]
    
    path = generate_excel_report(data, title="Test Excel")
    
    assert path.exists()
    assert path.suffix == ".excel"
    
    content = path.read_text()
    assert "Test Excel" in content
    
    # Cleanup
    path.unlink()


def test_generate_csv_report():
    """Test CSV report generation."""
    data = [
        {"Name": "John", "Age": 30},
        {"Name": "Jane", "Age": 25}
    ]
    
    path = generate_csv_report(data, title="Test CSV")
    
    assert path.exists()
    assert path.suffix == ".csv"
    
    content = path.read_text()
    lines = content.strip().split('\n')
    assert len(lines) == 3  # header + 2 data rows
    assert "Name" in lines[0]
    
    # Cleanup
    path.unlink()


def test_generate_report_all_formats():
    """Test generating all report formats."""
    data = [{"Name": "Test", "Value": 123}]
    
    # PDF
    pdf_path = generate_report(data, format="pdf", title="PDF Test")
    assert pdf_path.exists()
    pdf_path.unlink()
    
    # Excel
    excel_path = generate_report(data, format="excel", title="Excel Test")
    assert excel_path.exists()
    excel_path.unlink()
    
    # CSV
    csv_path = generate_report(data, format="csv", title="CSV Test")
    assert csv_path.exists()
    csv_path.unlink()


def test_report_generator_with_config():
    """Test report generator with custom config."""
    generator = ReportGenerator()
    config = ReportConfig(
        title="Custom Report",
        format="pdf",
        page_size="letter",
        orientation="landscape"
    )
    
    data = [{"Field": "Value"}]
    path = generator.generate_pdf(config, data, "Custom Report")
    
    assert path.exists()
    
    # Cleanup
    path.unlink()


def test_report_scheduler():
    """Test report scheduler."""
    generator = ReportGenerator()
    scheduler = ReportScheduler(generator)
    
    config = ReportConfig(title="Scheduled Report")
    job_id = scheduler.schedule("monthly_report", config, "0 0 1 * *", ["admin@example.com"])
    
    assert job_id is not None


def test_report_with_empty_data():
    """Test report with no data."""
    data = []
    
    # CSV with empty data
    path = generate_csv_report(data, title="Empty Report")
    assert path.exists()
    path.unlink()


def test_report_with_complex_data():
    """Test report with complex data types."""
    data = [
        {
            "Name": "John Doe",
            "Email": "john@example.com",
            "Age": 30,
            "Score": 95.5,
            "Active": True,
            "Created": "2024-01-15"
        }
    ]
    
    path = generate_pdf_report(data, title="Complex Report")
    
    assert path.exists()
    content = path.read_text()
    assert "John Doe" in content
    assert "john@example.com" in content
    
    # Cleanup
    path.unlink()


def test_html_rendering():
    """Test HTML rendering in PDF."""
    generator = ReportGenerator()
    config = ReportConfig(title="HTML Test")
    
    data = [{"Column A": "Value A", "Column B": "Value B"}]
    path = generator.generate_pdf(config, data, "HTML Test")
    
    content = path.read_text()
    assert "<table>" in content
    assert "<th>Column A</th>" in content
    assert "<td>Value A</td>" in content
    
    # Cleanup
    path.unlink()


def test_excel_columns_with_formulas():
    """Test Excel columns with aggregate functions."""
    columns = [
        ExcelColumn(header="ID", field="id"),
        ExcelColumn(header="Total", field="total", aggregate="sum"),
        ExcelColumn(header="Count", field="id", aggregate="count")
    ]
    
    config = ExcelConfig(columns=columns)
    assert len(config.columns) == 3
    assert config.columns[1].aggregate == "sum"
    assert config.columns[2].aggregate == "count"


def test_report_output_path():
    """Test report output path generation."""
    generator = ReportGenerator()
    config = ReportConfig(title="Path Test")
    
    path = generator._get_output_path(config, "pdf", "Path Test")
    
    assert path.suffix == ".pdf"
    assert "Path Test" in path.name or "pathtest" in path.name.lower()


def test_report_with_styles():
    """Test report with custom styles."""
    generator = ReportGenerator()
    config = ReportConfig(
        title="Styled Report",
        styles={
            "header": {"color": "#333", "font-size": "24px"},
            "table": {"border": "1px solid #ccc"}
        }
    )
    
    data = [{"Field": "Value"}]
    path = generator.generate_pdf(config, data, "Styled Report")
    
    assert path.exists()
    
    # Cleanup
    path.unlink()