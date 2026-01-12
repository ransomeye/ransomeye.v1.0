#!/usr/bin/env python3
"""
RansomEye Signed Reporting Engine - Branding Module
AUTHORITATIVE: Visual identity and branding (presentation-only, outside integrity boundary)
"""

import os
from pathlib import Path
from typing import Optional


class BrandingError(Exception):
    """Base exception for branding errors."""
    pass


class Branding:
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
    
    @staticmethod
    def get_logo_path() -> Optional[Path]:
        """
        Get logo path from environment variable or default.
        
        Returns:
            Logo path, or None if not found
        """
        logo_path_str = os.environ.get('RANSOMEYE_LOGO_PATH', str(Branding.DEFAULT_LOGO_PATH))
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
        logo_path = Branding.get_logo_path()
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
        return Branding.PRODUCT_NAME
    
    @staticmethod
    def get_evidence_notice() -> str:
        """
        Get evidence notice text.
        
        Returns:
            Evidence notice text
        """
        return Branding.EVIDENCE_NOTICE
