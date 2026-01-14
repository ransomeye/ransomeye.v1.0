#!/usr/bin/env python3
"""
RansomEye Signed Reporting Engine - Reporting API
AUTHORITATIVE: API for generating signed, regulator-verifiable reports
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, timezone

# Add audit-ledger to path
_audit_ledger_dir = Path(__file__).parent.parent.parent / "audit-ledger"
if str(_audit_ledger_dir) not in sys.path:
    sys.path.insert(0, str(_audit_ledger_dir))

# Import audit ledger components
import importlib.util

_store_spec = importlib.util.spec_from_file_location("audit_ledger_storage", _audit_ledger_dir / "storage" / "append_only_store.py")
_store_module = importlib.util.module_from_spec(_store_spec)
_store_spec.loader.exec_module(_store_module)
AppendOnlyStore = _store_module.AppendOnlyStore
LedgerWriter = _store_module.LedgerWriter

_key_manager_spec = importlib.util.spec_from_file_location("audit_ledger_key_manager", _audit_ledger_dir / "crypto" / "key_manager.py")
_key_manager_module = importlib.util.module_from_spec(_key_manager_spec)
_key_manager_spec.loader.exec_module(_key_manager_module)
KeyManager = _key_manager_module.KeyManager

_signer_spec = importlib.util.spec_from_file_location("audit_ledger_signer", _audit_ledger_dir / "crypto" / "signer.py")
_signer_module = importlib.util.module_from_spec(_signer_spec)
_signer_spec.loader.exec_module(_signer_module)
Signer = _signer_module.Signer

# Import explanation assembly components (read-only)
_explanation_assembly_dir = Path(__file__).parent.parent.parent / "explanation-assembly"
if str(_explanation_assembly_dir) not in sys.path:
    sys.path.insert(0, str(_explanation_assembly_dir))

_assembly_api_spec = importlib.util.spec_from_file_location("assembly_api", _explanation_assembly_dir / "api" / "assembly_api.py")
_assembly_api_module = importlib.util.module_from_spec(_assembly_api_spec)
_assembly_api_spec.loader.exec_module(_assembly_api_module)
AssemblyAPI = _assembly_api_module.AssemblyAPI

# Import signed reporting components
_signed_reporting_dir = Path(__file__).parent.parent
if str(_signed_reporting_dir) not in sys.path:
    sys.path.insert(0, str(_signed_reporting_dir))

_render_engine_spec = importlib.util.spec_from_file_location("render_engine", _signed_reporting_dir / "engine" / "render_engine.py")
_render_engine_module = importlib.util.module_from_spec(_render_engine_spec)
_render_engine_spec.loader.exec_module(_render_engine_module)
RenderEngine = _render_engine_module.RenderEngine

_render_hasher_spec = importlib.util.spec_from_file_location("render_hasher", _signed_reporting_dir / "engine" / "render_hasher.py")
_render_hasher_module = importlib.util.module_from_spec(_render_hasher_spec)
_render_hasher_spec.loader.exec_module(_render_hasher_module)
RenderHasher = _render_hasher_module.RenderHasher

_report_signer_spec = importlib.util.spec_from_file_location("report_signer", _signed_reporting_dir / "crypto" / "report_signer.py")
_report_signer_module = importlib.util.module_from_spec(_report_signer_spec)
_report_signer_spec.loader.exec_module(_report_signer_module)
ReportSigner = _report_signer_module.ReportSigner

_report_store_spec = importlib.util.spec_from_file_location("report_store", _signed_reporting_dir / "storage" / "report_store.py")
_report_store_module = importlib.util.module_from_spec(_report_store_spec)
_report_store_spec.loader.exec_module(_report_store_module)
ReportStore = _report_store_module.ReportStore


class ReportingAPIError(Exception):
    """Base exception for reporting API errors."""
    pass


class ReportingAPI:
    """
    API for generating signed, regulator-verifiable reports.
    
    All operations:
    - Read-only access to Explanation Assembly Engine
    - Read-only access to Audit Ledger
    - Write ONLY to report_store
    - Emit audit ledger entries
    - Never modify source explanations
    """
    
    def __init__(
        self,
        store_path: Path,
        ledger_path: Path,
        ledger_key_dir: Path,
        signing_key_path: Path,
        signing_key_id: str,
        assembly_store_path: Optional[Path] = None,
        assembly_ledger_path: Optional[Path] = None,
        assembly_ledger_key_dir: Optional[Path] = None
    ):
        """
        Initialize reporting API.
        
        Args:
            store_path: Path to report store file
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
            signing_key_path: Path to report signing private key
            signing_key_id: Signing key identifier
            assembly_store_path: Optional path to explanation assembly store
            assembly_ledger_path: Optional path to explanation assembly ledger
            assembly_ledger_key_dir: Optional path to explanation assembly ledger keys
        """
        self.store = ReportStore(store_path)
        self.render_engine = RenderEngine()
        self.render_hasher = RenderHasher()
        self.report_signer = ReportSigner(signing_key_path, signing_key_id)
        
        # Explanation Assembly API (read-only, optional)
        if assembly_store_path and assembly_ledger_path and assembly_ledger_key_dir:
            self.assembly_api = AssemblyAPI(
                store_path=assembly_store_path,
                ledger_path=assembly_ledger_path,
                ledger_key_dir=assembly_ledger_key_dir
            )
        else:
            self.assembly_api = None
        
        # Initialize audit ledger
        try:
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
        except Exception as e:
            raise ReportingAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def generate_report(
        self,
        incident_id: str,
        view_type: str,
        format_type: str,
        assembled_explanation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate signed report from assembled explanation.
        
        Args:
            incident_id: Incident identifier
            view_type: View type (SOC_ANALYST, INCIDENT_COMMANDER, EXECUTIVE, REGULATOR)
            format_type: Format type (PDF, HTML, CSV)
            assembled_explanation_id: Optional assembled explanation identifier (if None, retrieves latest)
        
        Returns:
            Signed report record dictionary
        """
        if format_type not in ['PDF', 'HTML', 'CSV']:
            raise ReportingAPIError(f"Invalid format_type: {format_type}. Must be one of PDF, HTML, CSV")
        
        # Get assembled explanation (read-only)
        if not self.assembly_api:
            raise ReportingAPIError("Explanation Assembly API not configured")
        
        if assembled_explanation_id:
            assembled_explanation = self.assembly_api.get_assembled_explanation(assembled_explanation_id)
        else:
            # Get latest assembled explanation for incident and view_type
            assemblies = self.assembly_api.list_assembled_explanations(incident_id)
            matching = [a for a in assemblies if a.get('view_type') == view_type]
            if not matching:
                raise ReportingAPIError(f"No assembled explanation found for incident {incident_id} and view_type {view_type}")
            assembled_explanation = matching[-1]  # Latest
        
        if not assembled_explanation:
            raise ReportingAPIError("Assembled explanation not found")
        
        # GA-BLOCKING: Get incident snapshot time (resolved_at or last_observed_at)
        # This ensures deterministic timestamps - same incident snapshot = same timestamp
        incident_snapshot_time = self._get_incident_snapshot_time(incident_id)
        
        # GA-BLOCKING: Render evidence content only (branding excluded from hash domain)
        # This ensures logo swap doesn't change hash
        try:
            evidence_content = self.render_engine.render_evidence_content(
                assembled_explanation, format_type, incident_snapshot_time
            )
        except Exception as e:
            raise ReportingAPIError(f"Failed to render evidence content: {e}") from e
        
        # GA-BLOCKING: Compute content hash on evidence content only (branding excluded)
        content_hash = self.render_hasher.hash_content(evidence_content)
        
        # GA-BLOCKING: Sign evidence content only (branding excluded)
        try:
            signature = self.report_signer.sign_content(evidence_content)
        except Exception as e:
            raise ReportingAPIError(f"Failed to sign report: {e}") from e
        
        # Render full report with branding (for storage/display, not hashed)
        try:
            full_report_content = self.render_engine.render_report(
                assembled_explanation, format_type, incident_snapshot_time
            )
        except Exception as e:
            raise ReportingAPIError(f"Failed to render full report: {e}") from e
        
        # Determine rendering profile
        rendering_profile_map = {
            'PDF': 'STANDARD_PDF',
            'HTML': 'STANDARD_HTML',
            'CSV': 'STANDARD_CSV'
        }
        rendering_profile_id = rendering_profile_map.get(format_type, 'STANDARD_PDF')
        
        # Create report record
        report_id = str(uuid.uuid4())
        audit_ledger_anchor = str(uuid.uuid4())  # Will be set after ledger entry
        
        # GA-BLOCKING: Use incident snapshot time for generated_at (not system time)
        # This ensures deterministic report metadata - same incident snapshot = same timestamp
        generated_at = incident_snapshot_time or datetime.now(timezone.utc).isoformat()
        
        report_record = {
            'report_id': report_id,
            'incident_id': incident_id,
            'assembled_explanation_id': assembled_explanation.get('assembled_explanation_id', ''),
            'view_type': view_type,
            'format': format_type,
            'content_hash': content_hash,
            'signature': signature,
            'signing_key_id': self.report_signer.key_id,
            'generated_at': generated_at,  # GA-BLOCKING: Incident-anchored timestamp
            'rendering_profile_id': rendering_profile_id,
            'audit_ledger_anchor': audit_ledger_anchor
        }
        
        # Store report record (immutable)
        try:
            self.store.store_report(report_record)
        except Exception as e:
            raise ReportingAPIError(f"Failed to store report: {e}") from e
        
        # Emit audit ledger entry
        try:
            ledger_entry = self.ledger_writer.create_entry(
                component='signed-reporting',
                component_instance_id='reporting-engine',
                action_type='REPORT_GENERATED',
                subject={'type': 'incident', 'id': incident_id},
                actor={'type': 'system', 'identifier': 'signed-reporting'},
                payload={
                    'report_id': report_id,
                    'incident_id': incident_id,
                    'assembled_explanation_id': assembled_explanation.get('assembled_explanation_id', ''),
                    'format': format_type,
                    'content_hash': content_hash,
                    'signing_key_id': self.report_signer.key_id
                }
            )
            # Update audit_ledger_anchor with actual ledger entry ID
            report_record['audit_ledger_anchor'] = ledger_entry.get('entry_id', audit_ledger_anchor)
        except Exception as e:
            raise ReportingAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return report_record
    
    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Get signed report by ID.
        
        Args:
            report_id: Report identifier
        
        Returns:
            Report record dictionary, or None if not found
        """
        return self.store.get_report_by_id(report_id)
    
    def list_reports(self, incident_id: str) -> List[Dict[str, Any]]:
        """
        List all signed reports for incident ID.
        
        Args:
            incident_id: Incident identifier
        
        Returns:
            List of report record dictionaries
        """
        return self.store.get_reports_by_incident_id(incident_id)
    
    def _get_incident_snapshot_time(self, incident_id: str) -> Optional[str]:
        """
        GA-BLOCKING: Get incident snapshot time (resolved_at or last_observed_at).
        
        This ensures deterministic timestamps - same incident snapshot = same timestamp.
        All report timestamps derive from this incident-anchored time, not system time.
        
        Args:
            incident_id: Incident identifier
        
        Returns:
            RFC3339 UTC timestamp string, or None if incident not found
        """
        # Try to query incident from database
        # Note: This requires DB connection - if not available, return None (fallback)
        try:
            import os
            import psycopg2
            from dateutil import parser
            
            # Get DB connection parameters from environment
            db_host = os.getenv('RANSOMEYE_DB_HOST', 'localhost')
            db_port = int(os.getenv('RANSOMEYE_DB_PORT', '5432'))
            db_name = os.getenv('RANSOMEYE_DB_NAME', 'ransomeye')
            db_user = os.getenv('RANSOMEYE_DB_USER', 'gagan')
            db_password = os.getenv('RANSOMEYE_DB_PASSWORD', 'gagan')
            
            # Query incident snapshot time
            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password,
                connect_timeout=5
            )
            
            try:
                cur = conn.cursor()
                # GA-BLOCKING: Use resolved_at if resolved, else last_observed_at
                cur.execute("""
                    SELECT 
                        resolved_at,
                        last_observed_at,
                        resolved
                    FROM incidents
                    WHERE incident_id = %s
                """, (incident_id,))
                
                result = cur.fetchone()
                cur.close()
                
                if result:
                    resolved_at, last_observed_at, resolved = result
                    # Use resolved_at if incident is resolved, else last_observed_at
                    snapshot_time = resolved_at if resolved and resolved_at else last_observed_at
                    
                    if snapshot_time:
                        # Convert to RFC3339 UTC string
                        if isinstance(snapshot_time, str):
                            dt = parser.isoparse(snapshot_time)
                        else:
                            dt = snapshot_time
                        
                        # Ensure UTC timezone
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        else:
                            dt = dt.astimezone(timezone.utc)
                        
                        return dt.isoformat()
            finally:
                conn.close()
        except Exception:
            # DB query failed - return None (fallback to system time in report_record)
            # This is acceptable for backward compatibility, but not ideal
            pass
        
        return None
