#!/usr/bin/env python3
"""
RansomEye Signed Reporting Engine - Render Engine
AUTHORITATIVE: Deterministic rendering of content blocks into human-consumable formats
"""

from typing import Dict, Any, List, Optional
import json
import csv
import io
from .branding import Branding


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
        format_type: str,
        incident_snapshot_time: Optional[str] = None
    ) -> bytes:
        """
        Render assembled explanation into specified format.
        
        GA-BLOCKING: Deterministic rendering with incident-anchored timestamps.
        All timestamps derive from incident snapshot time, not system time.
        
        Rules:
        - Deterministic: Same inputs → same output
        - No text rewriting
        - No summarization
        - No inference
        - No omission
        - Content blocks rendered as-is
        - All timestamps use incident_snapshot_time (not system time)
        
        Args:
            assembled_explanation: Assembled explanation dictionary (read-only)
            format_type: Format type (PDF, HTML, CSV)
            incident_snapshot_time: RFC3339 UTC timestamp of incident snapshot (resolved_at or last_observed_at)
        
        Returns:
            Rendered report as bytes (evidence content only, branding excluded from hash domain)
        """
        if format_type not in ['PDF', 'HTML', 'CSV']:
            raise RenderError(f"Invalid format_type: {format_type}. Must be one of PDF, HTML, CSV")
        
        view_type = assembled_explanation.get('view_type', '')
        content_blocks = assembled_explanation.get('content_blocks', [])
        incident_id = assembled_explanation.get('incident_id', '')
        
        # Sort content blocks by display_order (deterministic)
        sorted_blocks = sorted(content_blocks, key=lambda x: x.get('display_order', 0))
        
        if format_type == 'PDF':
            return self._render_pdf(incident_id, view_type, sorted_blocks, incident_snapshot_time)
        elif format_type == 'HTML':
            return self._render_html(incident_id, view_type, sorted_blocks, incident_snapshot_time)
        elif format_type == 'CSV':
            return self._render_csv(incident_id, view_type, sorted_blocks, incident_snapshot_time)
        else:
            raise RenderError(f"Unsupported format: {format_type}")
    
    def render_evidence_content(
        self,
        assembled_explanation: Dict[str, Any],
        format_type: str,
        incident_snapshot_time: Optional[str] = None
    ) -> bytes:
        """
        GA-BLOCKING: Render evidence content only (branding excluded from hash domain).
        
        This method returns only the evidence content, without branding header/footer.
        The hash is computed on this content only, ensuring branding changes don't affect hash.
        
        Args:
            assembled_explanation: Assembled explanation dictionary (read-only)
            format_type: Format type (PDF, HTML, CSV)
            incident_snapshot_time: RFC3339 UTC timestamp of incident snapshot
        
        Returns:
            Evidence content as bytes (no branding)
        """
        if format_type not in ['PDF', 'HTML', 'CSV']:
            raise RenderError(f"Invalid format_type: {format_type}. Must be one of PDF, HTML, CSV")
        
        view_type = assembled_explanation.get('view_type', '')
        content_blocks = assembled_explanation.get('content_blocks', [])
        incident_id = assembled_explanation.get('incident_id', '')
        
        # Sort content blocks by display_order (deterministic)
        sorted_blocks = sorted(content_blocks, key=lambda x: x.get('display_order', 0))
        
        if format_type == 'PDF':
            return self._render_pdf_evidence_only(incident_id, view_type, sorted_blocks, incident_snapshot_time)
        elif format_type == 'HTML':
            return self._render_html_evidence_only(incident_id, view_type, sorted_blocks, incident_snapshot_time)
        elif format_type == 'CSV':
            return self._render_csv_evidence_only(incident_id, view_type, sorted_blocks, incident_snapshot_time)
        else:
            raise RenderError(f"Unsupported format: {format_type}")
    
    def _render_pdf(self, incident_id: str, view_type: str, content_blocks: List[Dict[str, Any]], 
                   incident_snapshot_time: Optional[str] = None) -> bytes:
        """
        Render PDF report with branding (full report for display).
        
        GA-BLOCKING: Branding is added in header/footer, but this method returns full report.
        Use render_evidence_content() to get hashable content only.
        
        Args:
            incident_id: Incident identifier
            view_type: View type
            content_blocks: Sorted content blocks
            incident_snapshot_time: RFC3339 UTC timestamp of incident snapshot (for display only)
        
        Returns:
            Full PDF report as bytes (includes branding)
        """
        # Get evidence content
        evidence_content = self._render_pdf_evidence_only(incident_id, view_type, content_blocks, incident_snapshot_time)
        
        # Add branding header/footer (presentation layer, outside hash domain)
        lines = []
        lines.append("=" * 80)
        lines.append(f"{Branding.get_product_name()} — Evidence Report")
        lines.append("=" * 80)
        lines.append("")
        
        # Evidence content (deterministic, hashable)
        lines.append(evidence_content.decode('utf-8'))
        
        # Footer (branding layer - outside signed content)
        lines.append("")
        lines.append("=" * 80)
        lines.append(f"{Branding.get_evidence_notice()}")
        lines.append("=" * 80)
        
        return '\n'.join(lines).encode('utf-8')
    
    def _render_pdf_evidence_only(self, incident_id: str, view_type: str, content_blocks: List[Dict[str, Any]],
                                  incident_snapshot_time: Optional[str] = None) -> bytes:
        """
        GA-BLOCKING: Render evidence content only (no branding, hashable).
        
        This is the content that is hashed. Branding is excluded.
        All timestamps use incident_snapshot_time (not system time).
        
        Args:
            incident_id: Incident identifier
            view_type: View type
            content_blocks: Sorted content blocks
            incident_snapshot_time: RFC3339 UTC timestamp of incident snapshot (deterministic)
        
        Returns:
            Evidence content as bytes (no branding, deterministic)
        """
        lines = []
        
        # Evidence content (deterministic, hashable)
        lines.append(f"RANSOMEYE SIGNED REPORT")
        lines.append(f"Incident ID: {incident_id}")
        lines.append(f"View Type: {view_type}")
        
        # GA-BLOCKING: Use incident snapshot time (not system time)
        if incident_snapshot_time:
            lines.append(f"Incident Snapshot Time: {incident_snapshot_time}")
        else:
            # Fallback: Use empty string (deterministic)
            lines.append(f"Incident Snapshot Time: N/A")
        
        lines.append("")
        lines.append("CONTENT BLOCKS:")
        lines.append("")
        
        # Stable field ordering (deterministic)
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
    
    def _render_html(self, incident_id: str, view_type: str, content_blocks: List[Dict[str, Any]],
                    incident_snapshot_time: Optional[str] = None) -> bytes:
        """
        Render HTML report (deterministic, no rewriting).
        
        Branding is added in <header> block only, outside signed content hash boundary.
        
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
        html_lines.append(f'<title>{Branding.get_product_name()} Signed Report</title>')
        html_lines.append('<meta charset="utf-8">')
        html_lines.append('</head>')
        html_lines.append('<body>')
        
        # Header (branding layer - outside signed content)
        html_lines.append('<header>')
        logo_base64 = Branding.get_logo_base64()
        if logo_base64:
            html_lines.append(f'<img src="data:image/png;base64,{logo_base64}" alt="{Branding.get_product_name()}" style="max-height: 50px;">')
        html_lines.append(f'<h1>{Branding.get_product_name()} — Evidence Report</h1>')
        html_lines.append('</header>')
        
        # Signed content (deterministic, hashable)
        html_lines.append('<main>')
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
        html_lines.append('</main>')
        
        # Footer (branding layer - outside signed content)
        html_lines.append('<footer>')
        html_lines.append(f'<p><em>{Branding.get_evidence_notice()}</em></p>')
        html_lines.append('</footer>')
        
        html_lines.append('</body>')
        html_lines.append('</html>')
        
        return '\n'.join(html_lines).encode('utf-8')
    
    def _render_csv(self, incident_id: str, view_type: str, content_blocks: List[Dict[str, Any]]) -> bytes:
        """
        Render CSV report (deterministic, no rewriting).
        
        Branding is added as comment header line only, outside signed content hash boundary.
        
        Args:
            incident_id: Incident identifier
            view_type: View type
            content_blocks: Sorted content blocks
        
        Returns:
            CSV report as bytes
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Comment header (branding layer - outside signed content)
        output.write(f"# Generated by {Branding.get_product_name()}\n")
        output.write(f"# {Branding.get_evidence_notice()}\n")
        output.write("\n")
        
        # Signed content (deterministic, hashable)
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
