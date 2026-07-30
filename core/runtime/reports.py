"""PyGo Report Engine (v0.31.0).

Generates PDF, Excel, CSV reports from PyGo models.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from io import StringIO, BytesIO
import csv
import json
from datetime import datetime


@dataclass
class ReportColumn:
    """Defines a column in a report."""
    name: str
    label: str
    format: Optional[str] = None
    width: Optional[int] = None


@dataclass
class ReportDefinition:
    """Defines a report structure."""
    name: str
    title: str
    columns: List[ReportColumn]
    description: str = ""
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReportDefinition":
        """Create from dictionary definition."""
        columns = [
            ReportColumn(**col) for col in data.get("columns", [])
        ]
        return cls(
            name=data["name"],
            title=data["title"],
            columns=columns,
            description=data.get("description", "")
        )


class ReportEngine:
    """Generates reports in multiple formats."""
    
    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data
    
    def to_csv(self) -> str:
        """Export data to CSV format."""
        if not self.data:
            return ""
        
        output = StringIO()
        fieldnames = list(self.data[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(self.data)
        return output.getvalue()
    
    def to_excel(self) -> BytesIO:
        """Export data to Excel format."""
        try:
            import openpyxl
        except ImportError:
            raise ImportError("Excel export requires: pip install openpyxl")
        
        wb = openpyxl.Workbook()
        ws = wb.active
        
        if self.data:
            # Header row
            headers = list(self.data[0].keys())
            ws.append(headers)
            
            # Data rows
            for row in self.data:
                ws.append(list(row.values()))
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output
    
    def to_json(self, pretty: bool = False) -> str:
        """Export data to JSON format."""
        if pretty:
            return json.dumps(self.data, indent=2, default=str)
        return json.dumps(self.data, default=str)
    
    def to_pdf(self, template: Optional[str] = None) -> bytes:
        """Export data to PDF format."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
        except ImportError:
            raise ImportError("PDF export requires: pip install reportlab")
        
        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=letter)
        styles = getSampleStyleSheet()
        
        elements = []
        
        # Title
        if template:
            elements.append(Paragraph(template, styles['Title']))
        
        # Table data
        if self.data:
            headers = list(self.data[0].keys())
            data_rows = [headers]
            
            for row in self.data:
                data_rows.append([str(v) for v in row.values()])
            
            table = Table(data_rows)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
        
        doc.build(elements)
        output.seek(0)
        return output.read()


class ReportBuilder:
    """Builder for creating reports."""
    
    def __init__(self, definition: ReportDefinition):
        self.definition = definition
        self._filters: List[Dict[str, Any]] = []
        self._sort_by: Optional[str] = None
        self._group_by: Optional[str] = None
    
    def filter(self, field: str, operator: str, value: Any) -> "ReportBuilder":
        """Add a filter to the report."""
        self._filters.append({
            "field": field,
            "operator": operator,
            "value": value
        })
        return self
    
    def sort(self, field: str, descending: bool = False) -> "ReportBuilder":
        """Add sorting to the report."""
        self._sort_by = field
        return self
    
    def group_by(self, field: str) -> "ReportBuilder":
        """Add grouping to the report."""
        self._group_by = field
        return self
    
    def build(self, data: List[Dict[str, Any]]) -> ReportEngine:
        """Build the report engine with filtered data."""
        # Apply filters
        filtered = self._apply_filters(data)
        
        # Apply sorting
        if self._sort_by:
            filtered = sorted(filtered, key=lambda x: x.get(self._sort_by, ""))
        
        return ReportEngine(filtered)
    
    def _apply_filters(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply all filters to the data."""
        result = data
        for f in self._filters:
            field = f["field"]
            op = f["operator"]
            value = f["value"]
            
            if op == "eq":
                result = [r for r in result if r.get(field) == value]
            elif op == "ne":
                result = [r for r in result if r.get(field) != value]
            elif op == "contains":
                result = [r for r in result if value in str(r.get(field, ""))]
            elif op == "gt":
                result = [r for r in result if r.get(field, 0) > value]
            elif op == "lt":
                result = [r for r in result if r.get(field, 0) < value]
        
        return result


# Convenience functions
def generate_report(data: List[Dict[str, Any]], format: str = "csv") -> Any:
    """Generate a report in the specified format."""
    engine = ReportEngine(data)
    
    if format == "csv":
        return engine.to_csv()
    elif format == "excel":
        return engine.to_excel()
    elif format == "json":
        return engine.to_json()
    elif format == "pdf":
        return engine.to_pdf()
    else:
        raise ValueError(f"Unsupported format: {format}")


def create_report(name: str, title: str, columns: List[Dict[str, Any]]) -> ReportDefinition:
    """Create a report definition."""
    cols = [ReportColumn(**c) for c in columns]
    return ReportDefinition(name=name, title=title, columns=cols)