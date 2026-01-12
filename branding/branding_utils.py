#!/usr/bin/env python3
"""
RansomEye Branding & Visual Identity - Branding Utilities
AUTHORITATIVE: Visual identity utilities (presentation-only, outside integrity boundary)
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any


class BrandingUtils:
    """
    Visual identity and branding utilities.
    
    Properties:
    - Presentation-only: Never affects hashes, signatures, or evidence integrity
    - Environment-driven: Logo path from environment variable
    - Fail-open: No crashes on missing logo
    """
    
    # Authoritative logo path (default)
    DEFAULT_LOGO_PATH = Path('/home/ransomeye/rebuild/logo.png')
    
    # Product name
    PRODUCT_NAME = 'RansomEye'
    
    # Evidence notice
    EVIDENCE_NOTICE = 'This artifact is evidence-grade and cryptographically verifiable.'
    
    # Footer text
    FOOTER_TEXT = 'Evidence-grade system — Deterministic — Verifiable'
    
    @staticmethod
    def get_logo_path() -> Optional[Path]:
        """
        Get logo path from environment variable or default.
        
        Returns:
            Logo path, or None if not found
        """
        logo_path_str = os.environ.get('RANSOMEYE_LOGO_PATH', str(BrandingUtils.DEFAULT_LOGO_PATH))
        logo_path = Path(logo_path_str)
        
        if logo_path.exists():
            return logo_path
        return None
    
    @staticmethod
    def get_logo_base64() -> Optional[str]:
        """
        Get logo as base64-encoded string (for embedding in HTML/PDF).
        
        Returns:
            Base64-encoded logo, or None if logo not found
        """
        logo_path = BrandingUtils.get_logo_path()
        if not logo_path:
            return None
        
        try:
            import base64
            logo_bytes = logo_path.read_bytes()
            return base64.b64encode(logo_bytes).decode('ascii')
        except Exception:
            return None
    
    @staticmethod
    def get_product_name() -> str:
        """
        Get product name.
        
        Returns:
            Product name
        """
        return BrandingUtils.PRODUCT_NAME
    
    @staticmethod
    def get_evidence_notice() -> str:
        """
        Get evidence notice text.
        
        Returns:
            Evidence notice text
        """
        return BrandingUtils.EVIDENCE_NOTICE
    
    @staticmethod
    def get_footer_text() -> str:
        """
        Get footer text.
        
        Returns:
            Footer text
        """
        return BrandingUtils.FOOTER_TEXT
    
    @staticmethod
    def get_ui_branding_data() -> Dict[str, Any]:
        """
        Get UI branding data (for UI backend).
        
        Returns:
            Dictionary containing branding data
        """
        logo_path = BrandingUtils.get_logo_path()
        logo_base64 = BrandingUtils.get_logo_base64()
        
        return {
            'product_name': BrandingUtils.get_product_name(),
            'logo_path': str(logo_path) if logo_path else None,
            'logo_base64': logo_base64,
            'evidence_notice': BrandingUtils.get_evidence_notice(),
            'footer_text': BrandingUtils.get_footer_text(),
            'has_logo': logo_path is not None
        }
