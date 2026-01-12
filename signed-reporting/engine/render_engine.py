#!/usr/bin/env python3
"""
RansomEye Signed Reporting Engine - Render Engine
AUTHORITATIVE: Deterministic rendering of content blocks into human-consumable formats
"""

from typing import Dict, Any, List, Optional
import json
import csv
import io


class RenderError(Exception):
    """Base exception for render errors."""
    pass


class RenderEngine:
    """
    Deterministic rendering of content blocks into human-consumable formats.
    
    Properties:
    - Deterministic: Same inputs always produce same outputs
    - No rewriting: Content blocks rendered as-is
    - No summarization: No compression or omission
    - No inference: No new facts or interpretation
    - Fixed profiles: Static templates, not logic
    """
    
    # Rendering profiles (static templates, no logic)
    RENDERING_PROFILES = {
        'STANDARD_PDF': 'pdf',
        'STANDARD_HTML': 'html',
        'STANDARD_CSV': 'csv'
    }
    
    def __init__(self):
        """Initialize render engine."""
        pass
    
    def render_report(
        self,
        assembled_explanation: Dict[str, Any],
        format_type: str
    ) -> bytes:
        """
        Render assembled explanation into specified format.
        
        Rules:
        - Deterministic: Same inputs → same output
        - No text rewriting
        - No summarization
        - No inference
        - No omission
        - Content blocks rendered as-is
        
        Args:
            assembled_explanation: Assembled explanation dictionary (read-only)
            format_type: Format type (PDF, HTML, CSV)
        
        Returns:
            Rendered report as bytes
        """
        if format_type not in ['PDF', 'HTML', 'CSV']:
            raise RenderError(f"Invalid format_type: {format_type}. Must be one of PDF, HTML, CSV")
        
        view_type = assembled_explanation.get('view_type', '')
        content_blocks = assembled_explanation.get('content_blocks', [])
        incident_id = assembled_explanation.get('incident_id', '')
        
        # Sort content blocks by display_order (deterministic)
        sorted_blocks = sorted(content_blocks, key=lambda x: x.get('display_order', 0))
        
        if format_type == 'PDF':
            return self._render_pdf(incident_id, view_type, sorted_blocks)
        elif format_type == 'HTML':
            return self._render_html(incident_id, view_type, sorted_blocks)
        elif format_type == 'CSV':
            return self._render_csv(incident_id, view_type, sorted_blocks)
        else:
            raise RenderError(f"Unsupported format: {format_type}")
    
    def _render_pdf(self, incident_id: str, view_type: str, content_blocks: List[Dict[str, Any]]) -> bytes:
        """
        Render PDF report (deterministic, no rewriting).
        
        Args:
            incident_id: Incident identifier
            view_type: View type
            content_blocks: Sorted content blocks
        
        Returns:
            PDF report as bytes
        """
        # For Phase M7, generate a structured text representation
        # In production, this would use a PDF library (e.g., reportlab)
        # For now, generate deterministic text that can be converted to PDF
        
        lines = []
        lines.append(f"RANSOMEYE SIGNED REPORT")
        lines.append(f"Incident ID: {incident_id}")
        lines.append(f"View Type: {view_type}")
        lines.append("")
        lines.append("CONTENT BLOCKS:")
        lines.append("")
        
        for block in content_blocks:
            lines.append(f"Block ID: {block.get('block_id', '')}")
            lines.append(f"Source Type: {block.get('source_type', '')}")
            lines.append(f"Source ID: {block.get('source_id', '')}")
            lines.append(f"Content Type: {block.get('content_type', '')}")
            lines.append(f"Content Reference: {block.get('content_reference', '')}")
            lines.append(f"Display Order: {block.get('display_order', 0)}")
            lines.append("")
        
        # Convert to bytes (deterministic)
        return '\n'.join(lines).encode('utf-8')
    
    def _render_html(self, incident_id: str, view_type: str, content_blocks: List[Dict[str, Any]]) -> bytes:
        """
        Render HTML report (deterministic, no rewriting).
        
        Args:
            incident_id: Incident identifier
            view_type: View type
            content_blocks: Sorted content blocks
        
        Returns:
            HTML report as bytes
        """
        html_lines = []
        html_lines.append('<!DOCTYPE html>')
        html_lines.append('<html>')
        html_lines.append('<head>')
        html_lines.append('<title>RansomEye Signed Report</title>')
        html_lines.append('<meta charset="utf-8">')
        html_lines.append('</head>')
        html_lines.append('<body>')
        html_lines.append('<h1>RansomEye Signed Report</h1>')
        html_lines.append(f'<p><strong>Incident ID:</strong> {incident_id}</p>')
        html_lines.append(f'<p><strong>View Type:</strong> {view_type}</p>')
        html_lines.append('<h2>Content Blocks</h2>')
        html_lines.append('<table border="1">')
        html_lines.append('<tr><th>Block ID</th><th>Source Type</th><th>Source ID</th><th>Content Type</th><th>Content Reference</th><th>Display Order</th></tr>')
        
        for block in content_blocks:
            html_lines.append('<tr>')
            html_lines.append(f'<td>{block.get("block_id", "")}</td>')
            html_lines.append(f'<td>{block.get("source_type", "")}</td>')
            html_lines.append(f'<td>{block.get("source_id", "")}</td>')
            html_lines.append(f'<td>{block.get("content_type", "")}</td>')
            html_lines.append(f'<td>{block.get("content_reference", "")}</td>')
            html_lines.append(f'<td>{block.get("display_order", 0)}</td>')
            html_lines.append('</tr>')
        
        html_lines.append('</table>')
        html_lines.append('</body>')
        html_lines.append('</html>')
        
        return '\n'.join(html_lines).encode('utf-8')
    
    def _render_csv(self, incident_id: str, view_type: str, content_blocks: List[Dict[str, Any]]) -> bytes:
        """
        Render CSV report (deterministic, no rewriting).
        
        Args:
            incident_id: Incident identifier
            view_type: View type
            content_blocks: Sorted content blocks
        
        Returns:
            CSV report as bytes
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header row
        writer.writerow(['Incident ID', 'View Type', 'Block ID', 'Source Type', 'Source ID', 'Content Type', 'Content Reference', 'Display Order'])
        
        # Data rows
        for block in content_blocks:
            writer.writerow([
                incident_id,
                view_type,
                block.get('block_id', ''),
                block.get('source_type', ''),
                block.get('source_id', ''),
                block.get('content_type', ''),
                block.get('content_reference', ''),
                block.get('display_order', 0)
            ])
        
        return output.getvalue().encode('utf-8')
