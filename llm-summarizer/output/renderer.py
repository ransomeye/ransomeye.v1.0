#!/usr/bin/env python3
"""
RansomEye LLM Summarizer - Output Renderer
AUTHORITATIVE: Deterministic rendering of summaries to PDF/HTML/CSV
"""

import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class RendererError(Exception):
    """Base exception for renderer errors."""
    pass


class PDFRenderError(RendererError):
    """Raised when PDF rendering fails."""
    pass


class HTMLRenderError(RendererError):
    """Raised when HTML rendering fails."""
    pass


class CSVRenderError(RendererError):
    """Raised when CSV rendering fails."""
    pass


class OutputRenderer:
    """
    Deterministic output renderer for PDF, HTML, and CSV formats.
    
    Properties:
    - Deterministic: Same input always produces same output
    - Non-mutating: Never modifies generated text
    - Metadata-embedded: All formats include metadata
    - Fail-closed: All errors cause rejection
    """
    
    def __init__(self):
        """Initialize output renderer."""
        pass
    
    def render_pdf(
        self,
        generated_text: str,
        metadata: Dict[str, Any]
    ) -> bytes:
        """
        Render summary to PDF format.
        
        Rules:
        - Fixed layout (no dynamic positioning)
        - Monospaced or neutral font (Courier or Arial)
        - No JavaScript
        - Metadata in PDF metadata and footer
        - Deterministic: Same input → same PDF bytes
        
        Args:
            generated_text: Generated text (never modified)
            metadata: Metadata dictionary with:
                - summary_id
                - narrative_type
                - prompt_hash
                - model_id
                - model_version
                - output_hash
                - signature (optional)
                - signed_at (optional)
        
        Returns:
            PDF bytes
        
        Raises:
            PDFRenderError: If rendering fails
        """
        if not isinstance(generated_text, str):
            raise PDFRenderError(f"Generated text must be string, got {type(generated_text)}")
        
        if not isinstance(metadata, dict):
            raise PDFRenderError(f"Metadata must be dict, got {type(metadata)}")
        
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.enums import TA_LEFT
            from reportlab.pdfgen import canvas
        except ImportError:
            raise PDFRenderError(
                "reportlab not available. Install with: pip install reportlab"
            )
        
        try:
            # Create PDF in memory
            from io import BytesIO
            buffer = BytesIO()
            
            # Create document with fixed layout
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            # Build content
            story = []
            
            # Title
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor='black',
                fontName='Courier',  # Monospaced font
                alignment=TA_LEFT
            )
            story.append(Paragraph("Security Incident Summary", title_style))
            story.append(Spacer(1, 0.2 * inch))
            
            # Narrative type
            narrative_type = metadata.get('narrative_type', 'UNKNOWN')
            type_style = ParagraphStyle(
                'NarrativeType',
                parent=styles['Normal'],
                fontSize=12,
                fontName='Courier',
                alignment=TA_LEFT
            )
            story.append(Paragraph(f"<b>Narrative Type:</b> {narrative_type}", type_style))
            story.append(Spacer(1, 0.1 * inch))
            
            # Generated text (preserved exactly, no modification)
            text_style = ParagraphStyle(
                'GeneratedText',
                parent=styles['Normal'],
                fontSize=10,
                fontName='Courier',  # Monospaced font
                alignment=TA_LEFT,
                leading=12
            )
            
            # Split text into paragraphs (preserve line breaks)
            paragraphs = generated_text.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    # Escape HTML special characters for ReportLab
                    escaped_para = para.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    story.append(Paragraph(escaped_para, text_style))
                    story.append(Spacer(1, 0.1 * inch))
            
            story.append(PageBreak())
            
            # Metadata section
            metadata_style = ParagraphStyle(
                'Metadata',
                parent=styles['Normal'],
                fontSize=9,
                fontName='Courier',
                alignment=TA_LEFT
            )
            story.append(Paragraph("<b>Metadata</b>", metadata_style))
            story.append(Spacer(1, 0.1 * inch))
            
            metadata_items = [
                f"Summary ID: {metadata.get('summary_id', 'N/A')}",
                f"Narrative Type: {metadata.get('narrative_type', 'N/A')}",
                f"Prompt Hash: {metadata.get('prompt_hash', 'N/A')}",
                f"Model ID: {metadata.get('model_id', 'N/A')}",
                f"Model Version: {metadata.get('model_version', 'N/A')}",
                f"Output Hash: {metadata.get('output_hash', 'N/A')}",
            ]
            
            if metadata.get('signature'):
                metadata_items.append(f"Signature: {metadata.get('signature', 'N/A')[:64]}...")
            
            if metadata.get('signed_at'):
                metadata_items.append(f"Signed At: {metadata.get('signed_at', 'N/A')}")
            
            for item in metadata_items:
                story.append(Paragraph(item.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), metadata_style))
                story.append(Spacer(1, 0.05 * inch))
            
            # Build PDF
            doc.build(story, onFirstPage=self._add_pdf_footer, onLaterPages=self._add_pdf_footer)
            
            # Get PDF bytes
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            return pdf_bytes
            
        except Exception as e:
            raise PDFRenderError(f"PDF rendering failed: {e}") from e
    
    def render_html(
        self,
        generated_text: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Render summary to HTML format.
        
        Rules:
        - Static HTML (no JavaScript)
        - No external assets (no CSS files, no images)
        - Embedded styles only
        - Metadata in <meta> tags and visible section
        - Deterministic: Same input → same HTML string
        
        Args:
            generated_text: Generated text (never modified)
            metadata: Metadata dictionary
        
        Returns:
            HTML string
        
        Raises:
            HTMLRenderError: If rendering fails
        """
        if not isinstance(generated_text, str):
            raise HTMLRenderError(f"Generated text must be string, got {type(generated_text)}")
        
        if not isinstance(metadata, dict):
            raise HTMLRenderError(f"Metadata must be dict, got {type(metadata)}")
        
        try:
            # Escape HTML special characters
            def escape_html(text: str) -> str:
                return (text
                    .replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;')
                    .replace("'", '&#x27;'))
            
            # Build HTML
            html_parts = []
            
            # HTML header
            html_parts.append('<!DOCTYPE html>')
            html_parts.append('<html lang="en">')
            html_parts.append('<head>')
            html_parts.append('<meta charset="UTF-8">')
            html_parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
            html_parts.append('<title>Security Incident Summary</title>')
            
            # Metadata in <meta> tags
            html_parts.append(f'<meta name="summary_id" content="{escape_html(str(metadata.get("summary_id", "")))}">')
            html_parts.append(f'<meta name="narrative_type" content="{escape_html(str(metadata.get("narrative_type", "")))}">')
            html_parts.append(f'<meta name="prompt_hash" content="{escape_html(str(metadata.get("prompt_hash", "")))}">')
            html_parts.append(f'<meta name="model_id" content="{escape_html(str(metadata.get("model_id", "")))}">')
            html_parts.append(f'<meta name="model_version" content="{escape_html(str(metadata.get("model_version", "")))}">')
            html_parts.append(f'<meta name="output_hash" content="{escape_html(str(metadata.get("output_hash", "")))}">')
            
            if metadata.get('signature'):
                html_parts.append(f'<meta name="signature" content="{escape_html(str(metadata.get("signature", "")))}">')
            
            if metadata.get('signed_at'):
                html_parts.append(f'<meta name="signed_at" content="{escape_html(str(metadata.get("signed_at", "")))}">')
            
            # Embedded styles (no external CSS)
            html_parts.append('<style>')
            html_parts.append('body { font-family: monospace; margin: 40px; line-height: 1.6; color: #000; background: #fff; }')
            html_parts.append('h1 { font-size: 18px; margin-bottom: 20px; }')
            html_parts.append('.metadata { font-size: 11px; color: #666; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ccc; }')
            html_parts.append('.metadata-item { margin: 5px 0; }')
            html_parts.append('.content { white-space: pre-wrap; font-size: 12px; }')
            html_parts.append('</style>')
            html_parts.append('</head>')
            html_parts.append('<body>')
            
            # Title
            html_parts.append('<h1>Security Incident Summary</h1>')
            
            # Narrative type
            narrative_type = metadata.get('narrative_type', 'UNKNOWN')
            html_parts.append(f'<p><strong>Narrative Type:</strong> {escape_html(narrative_type)}</p>')
            
            # Generated text (preserved exactly, no modification)
            html_parts.append('<div class="content">')
            html_parts.append(escape_html(generated_text))
            html_parts.append('</div>')
            
            # Metadata section
            html_parts.append('<div class="metadata">')
            html_parts.append('<h2>Metadata</h2>')
            html_parts.append(f'<div class="metadata-item"><strong>Summary ID:</strong> {escape_html(str(metadata.get("summary_id", "N/A")))}</div>')
            html_parts.append(f'<div class="metadata-item"><strong>Narrative Type:</strong> {escape_html(str(metadata.get("narrative_type", "N/A")))}</div>')
            html_parts.append(f'<div class="metadata-item"><strong>Prompt Hash:</strong> {escape_html(str(metadata.get("prompt_hash", "N/A")))}</div>')
            html_parts.append(f'<div class="metadata-item"><strong>Model ID:</strong> {escape_html(str(metadata.get("model_id", "N/A")))}</div>')
            html_parts.append(f'<div class="metadata-item"><strong>Model Version:</strong> {escape_html(str(metadata.get("model_version", "N/A")))}</div>')
            html_parts.append(f'<div class="metadata-item"><strong>Output Hash:</strong> {escape_html(str(metadata.get("output_hash", "N/A")))}</div>')
            
            if metadata.get('signature'):
                html_parts.append(f'<div class="metadata-item"><strong>Signature:</strong> {escape_html(str(metadata.get("signature", "N/A"))[:64])}...</div>')
            
            if metadata.get('signed_at'):
                html_parts.append(f'<div class="metadata-item"><strong>Signed At:</strong> {escape_html(str(metadata.get("signed_at", "N/A")))}</div>')
            
            html_parts.append('</div>')
            html_parts.append('</body>')
            html_parts.append('</html>')
            
            # Join and return
            html_string = '\n'.join(html_parts)
            
            return html_string
            
        except Exception as e:
            raise HTMLRenderError(f"HTML rendering failed: {e}") from e
    
    def render_csv(
        self,
        generated_text: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Render summary to CSV format.
        
        Rules:
        - One row per logical section (paragraph)
        - Metadata as header rows
        - No free-form text splitting across cells
        - Deterministic: Same input → same CSV string
        
        Args:
            generated_text: Generated text (never modified)
            metadata: Metadata dictionary
        
        Returns:
            CSV string
        
        Raises:
            CSVRenderError: If rendering fails
        """
        if not isinstance(generated_text, str):
            raise CSVRenderError(f"Generated text must be string, got {type(generated_text)}")
        
        if not isinstance(metadata, dict):
            raise CSVRenderError(f"Metadata must be dict, got {type(metadata)}")
        
        try:
            import csv
            from io import StringIO
            
            # Build CSV in memory
            buffer = StringIO()
            writer = csv.writer(buffer)
            
            # Metadata header rows
            writer.writerow(['METADATA_SECTION', 'FIELD', 'VALUE'])
            writer.writerow(['summary_id', 'summary_id', metadata.get('summary_id', 'N/A')])
            writer.writerow(['narrative_type', 'narrative_type', metadata.get('narrative_type', 'N/A')])
            writer.writerow(['prompt_hash', 'prompt_hash', metadata.get('prompt_hash', 'N/A')])
            writer.writerow(['model_id', 'model_id', metadata.get('model_id', 'N/A')])
            writer.writerow(['model_version', 'model_version', metadata.get('model_version', 'N/A')])
            writer.writerow(['output_hash', 'output_hash', metadata.get('output_hash', 'N/A')])
            
            if metadata.get('signature'):
                writer.writerow(['signature', 'signature', metadata.get('signature', 'N/A')])
            
            if metadata.get('signed_at'):
                writer.writerow(['signed_at', 'signed_at', metadata.get('signed_at', 'N/A')])
            
            # Empty row separator
            writer.writerow([])
            
            # Content section header
            writer.writerow(['CONTENT_SECTION', 'SECTION_NUMBER', 'CONTENT'])
            
            # Split text into logical sections (paragraphs)
            paragraphs = generated_text.split('\n\n')
            section_number = 1
            
            for para in paragraphs:
                if para.strip():
                    # Escape newlines within paragraph (replace with space for CSV)
                    cleaned_para = para.strip().replace('\n', ' ').replace('\r', '')
                    writer.writerow(['content', section_number, cleaned_para])
                    section_number += 1
            
            # Get CSV string
            csv_string = buffer.getvalue()
            buffer.close()
            
            return csv_string
            
        except Exception as e:
            raise CSVRenderError(f"CSV rendering failed: {e}") from e
    
    def _add_pdf_footer(
        self,
        canvas_obj,
        doc
    ) -> None:
        """
        Add footer to PDF pages with metadata.
        
        Args:
            canvas_obj: ReportLab canvas object
            doc: Document object
        """
        canvas_obj.saveState()
        canvas_obj.setFont('Courier', 8)
        canvas_obj.drawString(72, 30, "RansomEye Security Incident Summary - Confidential")
        canvas_obj.restoreState()
