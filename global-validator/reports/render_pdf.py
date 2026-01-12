#!/usr/bin/env python3
"""
RansomEye Global Validator - PDF Report Renderer
AUTHORITATIVE: Render validation reports as PDF for human/compliance use
"""

from pathlib import Path
from typing import Dict, Any


class PDFRenderError(Exception):
    """Base exception for PDF rendering errors."""
    pass


def render_pdf(report: Dict[str, Any], output_path: Path) -> None:
    """
    Render validation report as PDF.
    
    Args:
        report: Validation report dictionary
        output_path: Path to output PDF file
    
    Raises:
        PDFRenderError: If PDF rendering fails
    """
    try:
        # Try to use reportlab if available
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            _REPORTLAB_AVAILABLE = True
        except ImportError:
            _REPORTLAB_AVAILABLE = False
        
        if not _REPORTLAB_AVAILABLE:
            # Fallback: create simple text-based PDF using basic approach
            # For production, install reportlab: pip install reportlab
            raise PDFRenderError("reportlab not available. Install with: pip install reportlab")
        
        # Create PDF document
        doc = SimpleDocTemplate(str(output_path), pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph("RansomEye Global Validator Report", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 0.2*inch))
        
        # Report metadata
        metadata = [
            ['Report ID:', report.get('report_id', 'N/A')],
            ['Timestamp:', report.get('timestamp', 'N/A')],
            ['Validator Version:', report.get('validator_version', 'N/A')],
            ['Validation Status:', report.get('validation_status', 'N/A')]
        ]
        
        metadata_table = Table(metadata, colWidths=[2*inch, 4*inch])
        metadata_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(metadata_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Check results
        checks = [
            ('Ledger Checks', report.get('ledger_checks', {})),
            ('Integrity Checks', report.get('integrity_checks', {})),
            ('Custody Checks', report.get('custody_checks', {})),
            ('Config Checks', report.get('config_checks', {})),
            ('Simulation Checks', report.get('simulation_checks', {}))
        ]
        
        for check_name, check_result in checks:
            if not check_result:
                continue
            
            status = check_result.get('status', 'N/A')
            status_color = colors.green if status == 'PASS' else colors.red
            
            check_header = Paragraph(f"<b>{check_name}</b> - Status: <font color='{'green' if status == 'PASS' else 'red'}'>{status}</font>", styles['Heading2'])
            story.append(check_header)
            story.append(Spacer(1, 0.1*inch))
            
            # Check details
            details = []
            for key, value in check_result.items():
                if key not in ('status', 'failures'):
                    details.append([key.replace('_', ' ').title(), str(value)])
            
            if details:
                details_table = Table(details, colWidths=[2*inch, 4*inch])
                details_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey)
                ]))
                story.append(details_table)
                story.append(Spacer(1, 0.2*inch))
        
        # Failure details
        first_failure = report.get('first_failure')
        if first_failure:
            failure_header = Paragraph("<b>First Failure Details</b>", styles['Heading2'])
            story.append(failure_header)
            story.append(Spacer(1, 0.1*inch))
            
            failure_details = [
                ['Check Type:', first_failure.get('check_type', 'N/A')],
                ['Location:', first_failure.get('location', 'N/A')],
                ['Error:', first_failure.get('error', 'N/A')]
            ]
            
            failure_table = Table(failure_details, colWidths=[2*inch, 4*inch])
            failure_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightcoral),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(failure_table)
            story.append(Spacer(1, 0.2*inch))
        
        # Signature
        signature_info = Paragraph(
            f"<b>Report Signature:</b><br/>"
            f"Key ID: {report.get('signing_key_id', 'N/A')}<br/>"
            f"Report Hash: {report.get('report_hash', 'N/A')}",
            styles['Normal']
        )
        story.append(signature_info)
        
        # Build PDF
        doc.build(story)
        
    except Exception as e:
        raise PDFRenderError(f"Failed to render PDF: {e}") from e
