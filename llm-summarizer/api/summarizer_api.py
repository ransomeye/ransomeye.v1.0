#!/usr/bin/env python3
"""
RansomEye LLM Summarizer - Summarizer API
AUTHORITATIVE: Main API with audit ledger integration
"""

import sys
import os
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
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

# Import summarizer components
from ..redaction.redaction_engine import RedactionEngine
from ..redaction.redaction_policy import RedactionPolicy
from ..prompts.template_registry import TemplateRegistry
from ..prompts.prompt_assembler import PromptAssembler
from ..prompts.prompt_hasher import PromptHasher
from ..llm.sandbox import Sandbox
from ..llm.model_loader import ModelLoader, ModelLoaderError
from ..llm.inference_engine import InferenceEngine, InferenceEngineError
from ..llm.token_manager import TokenManager
from ..output.validator import OutputValidator
from ..output.signer import OutputSigner
from ..output.renderer import OutputRenderer
from ..storage.summary_store import SummaryStore


class SummarizerAPIError(Exception):
    """Base exception for summarizer API errors."""
    pass


class SummarizerAPI:
    """
    Main summarizer API with audit ledger integration.
    
    All operations:
    - Redact PII (deterministic)
    - Assemble prompts (deterministic)
    - Execute in sandbox (foundation only, no inference yet)
    - Validate outputs
    - Sign outputs
    - Emit audit ledger entries (every operation)
    """
    
    def __init__(
        self,
        template_registry_path: Path,
        summary_store_path: Path,
        output_schema_path: Path,
        ledger_path: Path,
        ledger_key_dir: Path,
        model_registry_api: Optional[Any] = None,
        signing_key_path: Optional[Path] = None,
        signing_key_id: Optional[str] = None
    ):
        """
        Initialize summarizer API.
        
        Args:
            template_registry_path: Path to template registry store
            summary_store_path: Path to summary store
            output_schema_path: Path to summary-output.schema.json
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
            model_registry_api: Optional RegistryAPI instance
            signing_key_path: Optional path to output signing key
            signing_key_id: Optional signing key identifier
        """
        # Initialize components
        self.template_registry = TemplateRegistry(template_registry_path)
        self.prompt_assembler = PromptAssembler(self.template_registry)
        self.summary_store = SummaryStore(summary_store_path)
        self.output_validator = OutputValidator(output_schema_path)
        self.output_renderer = OutputRenderer()
        self.sandbox = Sandbox()
        self.model_loader = ModelLoader(model_registry_api=model_registry_api)
        
        # Model instance (loaded on first use)
        self.model_instance = None
        self.model_metadata = None
        self.inference_engine = None
        self.token_manager = TokenManager()
        
        if signing_key_path:
            self.output_signer = OutputSigner(signing_key_path, signing_key_id)
        else:
            self.output_signer = None
        
        # Initialize audit ledger
        try:
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
        except Exception as e:
            raise SummarizerAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def generate_summary(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate summary from request (foundation only - no actual inference yet).
        
        Process:
        1. Validate request
        2. Redact PII
        3. Assemble prompt
        4. Execute in sandbox (validation only, no inference)
        5. Validate output (placeholder)
        6. Sign output (if signer available)
        7. Store summary
        8. Emit audit entries
        
        Args:
            request: Summary request dictionary
        
        Returns:
            Summary output dictionary (with placeholder generated_text)
        
        Raises:
            SummarizerAPIError: If generation fails
        """
        summary_request_id = request.get('summary_request_id')
        narrative_type = request.get('narrative_type')
        redaction_policy_mode = request.get('redaction_policy')
        requested_by = request.get('requested_by')
        
        # Step 1: Redact PII
        try:
            policy = RedactionPolicy(redaction_policy_mode)
            redaction_engine = RedactionEngine(policy)
            redacted_data, redaction_log = redaction_engine.redact(
                data=request,
                summary_request_id=summary_request_id,
                redacted_by=requested_by
            )
        except Exception as e:
            raise SummarizerAPIError(f"PII redaction failed: {e}") from e
        
        # Emit audit entry: redaction completed
        try:
            self.ledger_writer.create_entry(
                component='llm-summarizer',
                component_instance_id='llm-summarizer',
                action_type='pii_redaction_completed',
                subject={'type': 'summary_request', 'id': summary_request_id},
                actor={'type': 'system', 'identifier': 'llm-summarizer'},
                payload={
                    'redaction_log_id': redaction_log['redaction_log_id'],
                    'redaction_policy': redaction_policy_mode,
                    'redaction_count': len(redaction_log['redactions'])
                }
            )
        except Exception as e:
            raise SummarizerAPIError(f"Failed to emit audit entry for redaction: {e}") from e
        
        # Step 2: Find template
        try:
            template_record = self.template_registry.find_template_by_narrative_type(narrative_type)
            if not template_record:
                raise SummarizerAPIError(f"Template not found for narrative type: {narrative_type}")
        except Exception as e:
            raise SummarizerAPIError(f"Template lookup failed: {e}") from e
        
        # Step 3: Assemble prompt
        try:
            prompt_result = self.prompt_assembler.assemble_prompt(
                template_id=template_record['template_id'],
                template_version=template_record['template_version'],
                input_facts=redacted_data
            )
        except Exception as e:
            raise SummarizerAPIError(f"Prompt assembly failed: {e}") from e
        
        # Emit audit entry: prompt assembled
        try:
            input_facts_hash = PromptHasher.hash_input_facts(redacted_data)
            self.ledger_writer.create_entry(
                component='llm-summarizer',
                component_instance_id='llm-summarizer',
                action_type='prompt_assembly_completed',
                subject={'type': 'summary_request', 'id': summary_request_id},
                actor={'type': 'system', 'identifier': 'llm-summarizer'},
                payload={
                    'prompt_hash': prompt_result['prompt_hash'],
                    'template_id': prompt_result['template_id'],
                    'template_version': prompt_result['template_version'],
                    'input_facts_hash': input_facts_hash
                }
            )
        except Exception as e:
            raise SummarizerAPIError(f"Failed to emit audit entry for prompt assembly: {e}") from e
        
        # Step 4: Load model if not already loaded
        # Model ID and version should come from request or config
        # For now, we'll use environment or default
        model_id = request.get('model_id') or os.getenv('RANSOMEYE_LLM_MODEL_ID', '')
        model_version = request.get('model_version') or os.getenv('RANSOMEYE_LLM_MODEL_VERSION', '1.0.0')
        
        if not model_id:
            raise SummarizerAPIError("Model ID not provided in request or environment")
        
        if not self.model_instance:
            try:
                self.model_instance, self.model_metadata = self.model_loader.load_model(
                    model_id=model_id,
                    model_version=model_version
                )
                
                # Initialize token manager with model
                self.token_manager.set_model(self.model_instance)
                
                # Initialize inference engine
                self.inference_engine = InferenceEngine(
                    model_instance=self.model_instance,
                    token_manager=self.token_manager,
                    max_output_tokens=1024,
                    max_execution_time_seconds=300
                )
            except ModelLoaderError as e:
                raise SummarizerAPIError(f"Model loading failed: {e}") from e
        
        # Emit audit entry: model loaded
        try:
            self.ledger_writer.create_entry(
                component='llm-summarizer',
                component_instance_id='llm-summarizer',
                action_type='llm_model_loaded',
                subject={'type': 'model', 'id': model_id},
                actor={'type': 'system', 'identifier': 'llm-summarizer'},
                payload={
                    'model_id': model_id,
                    'model_version': model_version,
                    'model_hash': self.model_metadata['model_hash'],
                    'lifecycle_state': self.model_metadata['lifecycle_state']
                }
            )
        except Exception as e:
            raise SummarizerAPIError(f"Failed to emit audit entry for model load: {e}") from e
        
        # Step 5: Execute inference in sandbox
        try:
            # Emit audit entry: inference started
            self.ledger_writer.create_entry(
                component='llm-summarizer',
                component_instance_id='llm-summarizer',
                action_type='llm_inference_started',
                subject={'type': 'summary_request', 'id': summary_request_id},
                actor={'type': 'system', 'identifier': 'llm-summarizer'},
                payload={
                    'model_id': model_id,
                    'model_version': model_version,
                    'prompt_hash': prompt_result['prompt_hash']
                }
            )
        except Exception as e:
            raise SummarizerAPIError(f"Failed to emit audit entry for inference start: {e}") from e
        
        try:
            inference_result = self.sandbox.execute_inference(
                inference_engine=self.inference_engine,
                prompt=prompt_result['prompt']
            )
            generated_text = inference_result['generated_text']
            input_tokens = inference_result['input_tokens']
            output_tokens = inference_result['output_tokens']
            inference_time_ms = inference_result['inference_time_ms']
            
            # Emit audit entry: inference completed
            try:
                self.ledger_writer.create_entry(
                    component='llm-summarizer',
                    component_instance_id='llm-summarizer',
                    action_type='llm_inference_completed',
                    subject={'type': 'summary_request', 'id': summary_request_id},
                    actor={'type': 'system', 'identifier': 'llm-summarizer'},
                    payload={
                        'model_id': model_id,
                        'model_version': model_version,
                        'model_hash': self.model_metadata['model_hash'],
                        'input_tokens': input_tokens,
                        'output_tokens': output_tokens,
                        'inference_time_ms': inference_time_ms,
                        'prompt_hash': prompt_result['prompt_hash']
                    }
                )
            except Exception as e:
                raise SummarizerAPIError(f"Failed to emit audit entry for inference completion: {e}") from e
        except Exception as e:
            # Emit audit entry: inference failed
            try:
                self.ledger_writer.create_entry(
                    component='llm-summarizer',
                    component_instance_id='llm-summarizer',
                    action_type='llm_inference_failed',
                    subject={'type': 'summary_request', 'id': summary_request_id},
                    actor={'type': 'system', 'identifier': 'llm-summarizer'},
                    payload={
                        'model_id': model_id,
                        'model_version': model_version,
                        'error': str(e),
                        'prompt_hash': prompt_result['prompt_hash']
                    }
                )
            except Exception:
                pass  # Don't fail on audit write failure during error handling
            
            raise SummarizerAPIError(f"Inference failed: {e}") from e
        
        # Step 6: Create summary output
        summary_id = str(uuid.uuid4())
        generated_at = datetime.now(timezone.utc).isoformat()
        
        # Step 6: Calculate output hash and sign (if signer available)
        if self.output_signer:
            try:
                signing_result = self.output_signer.sign_output(generated_text)
                output_hash = signing_result['output_hash']
                signature = signing_result['signature']
                signing_key_id = signing_result['signing_key_id']
            except Exception as e:
                raise SummarizerAPIError(f"Output signing failed: {e}") from e
        else:
            # Calculate hash without signing
            output_hash = hashlib.sha256(generated_text.encode('utf-8')).hexdigest()
            signature = ""
            signing_key_id = ""
        
        # Step 7: Build summary output
        summary_output = {
            'summary_id': summary_id,
            'summary_request_id': summary_request_id,
            'narrative_type': narrative_type,
            'generated_text': generated_text,
            'output_hash': output_hash,
            'signature': signature,
            'signing_key_id': signing_key_id,
            'prompt_template_id': prompt_result['template_id'],
            'prompt_template_version': prompt_result['template_version'],
            'prompt_hash': prompt_result['prompt_hash'],
            'model_id': model_id,
            'model_version': model_version,
            'redaction_log_id': redaction_log['redaction_log_id'],
            'generated_at': generated_at,
            'generated_by': requested_by
        }
        
        # Step 8: Validate output
        try:
            self.output_validator.validate(summary_output)
        except Exception as e:
            raise SummarizerAPIError(f"Output validation failed: {e}") from e
        
        # Step 9: Store summary
        try:
            self.summary_store.store_summary(summary_output)
        except Exception as e:
            raise SummarizerAPIError(f"Summary storage failed: {e}") from e
        
        # Step 10: Emit audit entry: summary generation completed
        try:
            self.ledger_writer.create_entry(
                component='llm-summarizer',
                component_instance_id='llm-summarizer',
                action_type='summary_generation_completed',
                subject={'type': 'summary', 'id': summary_id},
                actor={'type': 'system', 'identifier': 'llm-summarizer'},
                payload={
                    'summary_request_id': summary_request_id,
                    'narrative_type': narrative_type,
                    'output_hash': output_hash,
                    'signature': signature,
                    'prompt_hash': prompt_result['prompt_hash']
                }
            )
        except Exception as e:
            raise SummarizerAPIError(f"Failed to emit audit entry for summary generation: {e}") from e
        
        return summary_output
    
    def render_summary(
        self,
        summary_id: str,
        output_format: str
    ) -> bytes:
        """
        Render summary to specified format (PDF, HTML, or CSV).
        
        Process:
        1. Get summary from store
        2. Validate summary exists
        3. Extract metadata
        4. Render to requested format
        5. Emit audit entries
        
        Args:
            summary_id: Summary identifier
            output_format: Output format (PDF | HTML | CSV)
        
        Returns:
            Rendered output (bytes for PDF, str for HTML/CSV encoded as bytes)
        
        Raises:
            SummarizerAPIError: If rendering fails
        """
        # Validate output format
        valid_formats = ['PDF', 'HTML', 'CSV']
        if output_format.upper() not in valid_formats:
            raise SummarizerAPIError(
                f"Invalid output format: {output_format}. Must be one of: {valid_formats}"
            )
        
        output_format_upper = output_format.upper()
        
        # Get summary from store
        summary = self.summary_store.get_summary(summary_id)
        if not summary:
            raise SummarizerAPIError(f"Summary not found: {summary_id}")
        
        # Emit audit entry: render started
        try:
            self.ledger_writer.create_entry(
                component='llm-summarizer',
                component_instance_id='llm-summarizer',
                action_type='summary_render_started',
                subject={'type': 'summary', 'id': summary_id},
                actor={'type': 'system', 'identifier': 'llm-summarizer'},
                payload={
                    'summary_id': summary_id,
                    'output_format': output_format_upper,
                    'output_hash': summary.get('output_hash', '')
                }
            )
        except Exception as e:
            raise SummarizerAPIError(f"Failed to emit audit entry for render start: {e}") from e
        
        try:
            # Extract metadata
            metadata = {
                'summary_id': summary.get('summary_id', ''),
                'narrative_type': summary.get('narrative_type', ''),
                'prompt_hash': summary.get('prompt_hash', ''),
                'model_id': summary.get('model_id', ''),
                'model_version': summary.get('model_version', ''),
                'output_hash': summary.get('output_hash', ''),
                'signature': summary.get('signature', ''),
                'signed_at': summary.get('generated_at', '')  # Use generated_at as signed_at
            }
            
            generated_text = summary.get('generated_text', '')
            
            # Render based on format
            if output_format_upper == 'PDF':
                rendered_output = self.output_renderer.render_pdf(generated_text, metadata)
            elif output_format_upper == 'HTML':
                html_string = self.output_renderer.render_html(generated_text, metadata)
                rendered_output = html_string.encode('utf-8')
            elif output_format_upper == 'CSV':
                csv_string = self.output_renderer.render_csv(generated_text, metadata)
                rendered_output = csv_string.encode('utf-8')
            else:
                raise SummarizerAPIError(f"Unsupported output format: {output_format}")
            
            # Calculate rendered output hash (for audit)
            if isinstance(rendered_output, bytes):
                rendered_hash = hashlib.sha256(rendered_output).hexdigest()
            else:
                rendered_hash = hashlib.sha256(rendered_output.encode('utf-8')).hexdigest()
            
            # Emit audit entry: render completed
            try:
                self.ledger_writer.create_entry(
                    component='llm-summarizer',
                    component_instance_id='llm-summarizer',
                    action_type='summary_render_completed',
                    subject={'type': 'summary', 'id': summary_id},
                    actor={'type': 'system', 'identifier': 'llm-summarizer'},
                    payload={
                        'summary_id': summary_id,
                        'output_format': output_format_upper,
                        'output_hash': summary.get('output_hash', ''),
                        'rendered_hash': rendered_hash
                    }
                )
            except Exception as e:
                raise SummarizerAPIError(f"Failed to emit audit entry for render completion: {e}") from e
            
            return rendered_output
            
        except Exception as e:
            # Emit audit entry: render failed
            try:
                self.ledger_writer.create_entry(
                    component='llm-summarizer',
                    component_instance_id='llm-summarizer',
                    action_type='summary_render_failed',
                    subject={'type': 'summary', 'id': summary_id},
                    actor={'type': 'system', 'identifier': 'llm-summarizer'},
                    payload={
                        'summary_id': summary_id,
                        'output_format': output_format_upper,
                        'error': str(e),
                        'output_hash': summary.get('output_hash', '')
                    }
                )
            except Exception:
                pass  # Don't fail on audit write failure during error handling
            
            raise SummarizerAPIError(f"Rendering failed: {e}") from e
