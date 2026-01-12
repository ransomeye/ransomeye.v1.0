#!/usr/bin/env python3
"""
RansomEye Notification Engine - Dispatcher
AUTHORITATIVE: Dispatches deliveries to adapters (best-effort, no retries)
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
import importlib.util

# Add notification-engine to path
_notification_dir = Path(__file__).parent.parent
if str(_notification_dir) not in sys.path:
    sys.path.insert(0, str(_notification_dir))

# Import adapters
_email_adapter_spec = importlib.util.spec_from_file_location("email_adapter", _notification_dir / "adapters" / "email_adapter.py")
_email_adapter_module = importlib.util.module_from_spec(_email_adapter_spec)
_email_adapter_spec.loader.exec_module(_email_adapter_module)
EmailAdapter = _email_adapter_module.EmailAdapter

_webhook_adapter_spec = importlib.util.spec_from_file_location("webhook_adapter", _notification_dir / "adapters" / "webhook_adapter.py")
_webhook_adapter_module = importlib.util.module_from_spec(_webhook_adapter_spec)
_webhook_adapter_spec.loader.exec_module(_webhook_adapter_module)
WebhookAdapter = _webhook_adapter_module.WebhookAdapter

_ticket_adapter_spec = importlib.util.spec_from_file_location("ticket_adapter", _notification_dir / "adapters" / "ticket_adapter.py")
_ticket_adapter_module = importlib.util.module_from_spec(_ticket_adapter_spec)
_ticket_adapter_spec.loader.exec_module(_ticket_adapter_module)
TicketAdapter = _ticket_adapter_module.TicketAdapter

_siem_adapter_spec = importlib.util.spec_from_file_location("siem_adapter", _notification_dir / "adapters" / "siem_adapter.py")
_siem_adapter_module = importlib.util.module_from_spec(_siem_adapter_spec)
_siem_adapter_spec.loader.exec_module(_siem_adapter_module)
SIEMAdapter = _siem_adapter_module.SIEMAdapter


class DispatchError(Exception):
    """Base exception for dispatch errors."""
    pass


class Dispatcher:
    """
    Dispatches deliveries to adapters.
    
    Properties:
    - Best-effort: Delivery is best-effort, not guaranteed
    - No retries: Failure is recorded, not retried implicitly
    - Deterministic: Same payload always produces same delivery attempt
    """
    
    def __init__(self):
        """Initialize dispatcher."""
        self.email_adapter = EmailAdapter()
        self.webhook_adapter = WebhookAdapter()
        self.ticket_adapter = TicketAdapter()
        self.siem_adapter = SIEMAdapter()
    
    def dispatch(
        self,
        payload: Dict[str, Any],
        target: Dict[str, Any]
    ) -> bool:
        """
        Dispatch delivery to appropriate adapter.
        
        Args:
            payload: Formatted payload dictionary
            target: Target dictionary
        
        Returns:
            True if delivery succeeded, False otherwise
        """
        delivery_type = target.get('target_type', '')
        
        try:
            if delivery_type == 'email':
                return self.email_adapter.deliver(payload, target)
            elif delivery_type == 'webhook':
                return self.webhook_adapter.deliver(payload, target)
            elif delivery_type == 'ticket':
                return self.ticket_adapter.deliver(payload, target)
            elif delivery_type == 'siem':
                return self.siem_adapter.deliver(payload, target)
            else:
                return False
        except Exception:
            # Delivery failed, return False (failure is recorded, not retried)
            return False
