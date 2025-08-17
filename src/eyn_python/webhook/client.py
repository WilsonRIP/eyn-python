from __future__ import annotations

import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path

from ..api.client import APIClient, APIResponse


@dataclass
class WebhookClient:
    """Client for sending webhooks."""
    default_headers: Optional[Dict[str, str]] = None
    timeout: float = 30.0
    retries: int = 3
    retry_delay: float = 1.0
    
    def __post_init__(self):
        if self.default_headers is None:
            self.default_headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'eyn-webhook-client/1.0',
            }
    
    def send(
        self,
        url: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        method: str = 'POST',
        signature_header: Optional[str] = None,
        signature_secret: Optional[str] = None,
    ) -> APIResponse:
        """Send a webhook to the specified URL."""
        
        # Prepare headers
        request_headers = self.default_headers.copy() if self.default_headers else {}
        if headers:
            request_headers.update(headers)
        
        # Add webhook signature if requested
        if signature_header and signature_secret:
            signature = self._generate_signature(data, signature_secret)
            request_headers[signature_header] = signature
        
        # Create client and send request
        with APIClient(timeout=self.timeout) as client:
            for attempt in range(self.retries):
                try:
                    response = client.request(
                        method=method,
                        url=url,
                        headers=request_headers,
                        json_data=data,
                    )
                    return response
                    
                except Exception as e:
                    if attempt == self.retries - 1:  # Last attempt
                        raise
                    time.sleep(self.retry_delay * (attempt + 1))
        
        raise RuntimeError("Should not reach here")
    
    def _generate_signature(self, data: Dict[str, Any], secret: str) -> str:
        """Generate HMAC signature for webhook data."""
        import hmac
        import hashlib
        
        payload = json.dumps(data, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
    
    def send_multiple(
        self,
        urls: List[str],
        data: Dict[str, Any],
        **kwargs
    ) -> List[APIResponse]:
        """Send the same webhook to multiple URLs."""
        responses = []
        for url in urls:
            try:
                response = self.send(url, data, **kwargs)
                responses.append(response)
            except Exception as e:
                # Create a fake response for failed requests
                from ..api.client import APIResponse
                error_response = APIResponse(
                    status_code=0,
                    headers={},
                    text=f"Request failed: {e}",
                    url=url,
                    elapsed_ms=0.0,
                    request_method=kwargs.get('method', 'POST'),
                    request_headers={},
                )
                responses.append(error_response)
        
        return responses


def send_webhook(
    url: str,
    data: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    **kwargs
) -> APIResponse:
    """Quick function to send a webhook."""
    client = WebhookClient()
    return client.send(url, data, headers, **kwargs)


def simulate_webhook(
    webhook_type: str,
    data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """Simulate common webhook payloads."""
    
    templates = {
        'github_push': {
            'ref': 'refs/heads/main',
            'before': '0000000000000000000000000000000000000000',
            'after': 'abcdef1234567890abcdef1234567890abcdef12',
            'repository': {
                'id': 123456789,
                'name': 'test-repo',
                'full_name': 'user/test-repo',
                'html_url': 'https://github.com/user/test-repo',
            },
            'pusher': {
                'name': 'test-user',
                'email': 'user@example.com',
            },
            'commits': [
                {
                    'id': 'abcdef1234567890abcdef1234567890abcdef12',
                    'message': 'Test commit',
                    'author': {
                        'name': 'Test User',
                        'email': 'user@example.com',
                    },
                    'url': 'https://github.com/user/test-repo/commit/abcdef12',
                }
            ],
        },
        
        'stripe_payment': {
            'id': 'evt_test_webhook',
            'object': 'event',
            'api_version': '2020-08-27',
            'created': int(time.time()),
            'data': {
                'object': {
                    'id': 'pi_test_payment',
                    'object': 'payment_intent',
                    'amount': 2000,
                    'currency': 'usd',
                    'status': 'succeeded',
                    'customer': 'cus_test_customer',
                }
            },
            'livemode': False,
            'pending_webhooks': 1,
            'request': {
                'id': 'req_test_request',
                'idempotency_key': None,
            },
            'type': 'payment_intent.succeeded',
        },
        
        'slack_message': {
            'token': 'verification_token',
            'team_id': 'T1234567890',
            'team_domain': 'test-workspace',
            'channel_id': 'C1234567890',
            'channel_name': 'general',
            'user_id': 'U1234567890',
            'user_name': 'testuser',
            'command': '/test',
            'text': 'hello world',
            'response_url': 'https://hooks.slack.com/commands/1234/5678',
            'trigger_id': '123456789.987654321.abcdef',
        },
        
        'webhook_test': {
            'event': 'test',
            'timestamp': int(time.time()),
            'data': {
                'message': 'This is a test webhook',
                'source': 'eyn-webhook-simulator',
            },
        },
    }
    
    if webhook_type not in templates:
        available_types = ', '.join(templates.keys())
        raise ValueError(f"Unknown webhook type '{webhook_type}'. Available: {available_types}")
    
    payload = templates[webhook_type].copy()
    
    # Merge in custom data
    if data:
        payload.update(data)
    
    return payload


def load_webhook_templates(file_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load custom webhook templates from JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)


def save_webhook_template(
    name: str,
    template: Dict[str, Any],
    file_path: Path
):
    """Save a webhook template to file."""
    # Load existing templates
    if file_path.exists():
        templates = load_webhook_templates(file_path)
    else:
        templates = {}
    
    # Add new template
    templates[name] = template
    
    # Save back to file
    with open(file_path, 'w') as f:
        json.dump(templates, f, indent=2)
