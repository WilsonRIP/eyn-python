from __future__ import annotations

import time
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass

from .server import WebhookServer, WebhookRequest, WebhookResponse
from .client import WebhookClient, send_webhook


@dataclass
class WebhookTestResult:
    """Result of a webhook test."""
    success: bool
    message: str
    request: Optional[WebhookRequest] = None
    response_time_ms: float = 0.0
    error: Optional[str] = None


class WebhookTestServer:
    """Test server for webhook development and testing."""
    
    def __init__(self, port: int = 0):  # 0 = auto-select port
        self.server = WebhookServer(port=port, log_requests=False)
        self.received_webhooks: List[WebhookRequest] = []
        
        # Add handler to capture all webhooks
        def capture_handler(request: WebhookRequest) -> WebhookResponse:
            self.received_webhooks.append(request)
            return WebhookResponse(status_code=200, json_data={'status': 'received'})
        
        self.server.add_handler('/', capture_handler)
    
    def start(self):
        """Start the test server."""
        self.server.start()
        # Wait a bit for server to start
        time.sleep(0.1)
    
    def stop(self):
        """Stop the test server."""
        self.server.stop()
    
    def clear(self):
        """Clear received webhooks."""
        self.received_webhooks.clear()
        self.server.clear_requests()
    
    def wait_for_webhook(self, timeout: float = 5.0) -> Optional[WebhookRequest]:
        """Wait for a webhook to be received."""
        start_count = len(self.received_webhooks)
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if len(self.received_webhooks) > start_count:
                return self.received_webhooks[-1]
            time.sleep(0.1)
        
        return None
    
    def get_url(self, path: str = '/') -> str:
        """Get the URL for a specific path."""
        return f"http://{self.server.host}:{self.server.port}{path}"
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def test_webhook_endpoint(
    url: str,
    payload: Dict[str, Any],
    expected_status: int = 200,
    timeout: float = 10.0,
    headers: Optional[Dict[str, str]] = None,
) -> WebhookTestResult:
    """Test a webhook endpoint."""
    start_time = time.time()
    
    try:
        client = WebhookClient(timeout=timeout)
        response = client.send(url, payload, headers=headers)
        
        response_time = (time.time() - start_time) * 1000
        
        if response.status_code == expected_status:
            return WebhookTestResult(
                success=True,
                message=f"Webhook sent successfully (status: {response.status_code})",
                response_time_ms=response_time,
            )
        else:
            return WebhookTestResult(
                success=False,
                message=f"Unexpected status code: {response.status_code} (expected: {expected_status})",
                response_time_ms=response_time,
            )
    
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return WebhookTestResult(
            success=False,
            message=f"Webhook test failed: {e}",
            response_time_ms=response_time,
            error=str(e),
        )


def capture_webhooks(
    port: int = 8080,
    timeout: float = 30.0,
    count: int = 1,
) -> List[WebhookRequest]:
    """Capture incoming webhooks for testing."""
    
    captured = []
    
    with WebhookTestServer(port=port) as server:
        print(f"Webhook capture server running on {server.get_url()}")
        print(f"Waiting for {count} webhook(s) for {timeout} seconds...")
        
        start_time = time.time()
        
        while len(captured) < count and (time.time() - start_time) < timeout:
            webhook = server.wait_for_webhook(timeout=1.0)
            if webhook:
                captured.append(webhook)
                print(f"Captured webhook {len(captured)}: {webhook.method} {webhook.path}")
        
        if len(captured) < count:
            print(f"Timeout: Only captured {len(captured)}/{count} webhooks")
    
    return captured


class WebhookValidator:
    """Validate webhook signatures and content."""
    
    @staticmethod
    def validate_github_signature(payload: str, signature: str, secret: str) -> bool:
        """Validate GitHub webhook signature."""
        import hmac
        import hashlib
        
        if not signature.startswith('sha256='):
            return False
        
        expected_signature = 'sha256=' + hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    @staticmethod
    def validate_stripe_signature(payload: str, signature: str, secret: str) -> bool:
        """Validate Stripe webhook signature."""
        import hmac
        import hashlib
        
        try:
            # Stripe signature format: t=timestamp,v1=signature
            elements = signature.split(',')
            timestamp = None
            signatures = []
            
            for element in elements:
                if element.startswith('t='):
                    timestamp = element[2:]
                elif element.startswith('v1='):
                    signatures.append(element[3:])
            
            if not timestamp or not signatures:
                return False
            
            # Create expected signature
            signed_payload = f"{timestamp}.{payload}"
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                signed_payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Compare with any of the provided signatures
            return any(hmac.compare_digest(expected_signature, sig) for sig in signatures)
            
        except Exception:
            return False
    
    @staticmethod
    def validate_json_structure(data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """Validate JSON structure against a simple schema."""
        errors = []
        
        def check_field(obj, field_schema, path=""):
            if isinstance(field_schema, dict):
                if 'required' in field_schema and field_schema['required']:
                    for field in field_schema.get('fields', {}):
                        if field not in obj:
                            errors.append(f"Missing required field: {path}.{field}")
                
                for field, sub_schema in field_schema.get('fields', {}).items():
                    if field in obj:
                        check_field(obj[field], sub_schema, f"{path}.{field}" if path else field)
            
            elif isinstance(field_schema, str):
                # Type check
                expected_type = {
                    'string': str,
                    'number': (int, float),
                    'integer': int,
                    'boolean': bool,
                    'array': list,
                    'object': dict,
                }.get(field_schema)
                
                if expected_type and not isinstance(obj, expected_type):
                    errors.append(f"Field {path} should be {field_schema}, got {type(obj).__name__}")
        
        check_field(data, schema)
        return errors
