from __future__ import annotations

import json
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import uuid

try:
    from flask import Flask, request, jsonify, Response
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False


@dataclass
class WebhookRequest:
    """Incoming webhook request data."""
    id: str
    timestamp: datetime
    method: str
    url: str
    path: str
    headers: Dict[str, str]
    query_params: Dict[str, str]
    body: str
    json_data: Optional[Dict[str, Any]] = None
    content_type: str = ""
    remote_addr: str = ""
    user_agent: str = ""
    
    @classmethod
    def from_flask_request(cls, flask_req) -> 'WebhookRequest':
        """Create WebhookRequest from Flask request."""
        body = flask_req.get_data(as_text=True)
        
        try:
            json_data = flask_req.get_json() if flask_req.is_json else None
        except Exception:
            json_data = None
        
        return cls(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            method=flask_req.method,
            url=flask_req.url,
            path=flask_req.path,
            headers=dict(flask_req.headers),
            query_params=dict(flask_req.args),
            body=body,
            json_data=json_data,
            content_type=flask_req.content_type or "",
            remote_addr=flask_req.remote_addr or "",
            user_agent=flask_req.user_agent.string if flask_req.user_agent else "",
        )


@dataclass
class WebhookResponse:
    """Webhook response configuration."""
    status_code: int = 200
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    json_data: Optional[Dict[str, Any]] = None
    delay_seconds: float = 0.0
    
    def to_flask_response(self) -> Response:
        """Convert to Flask Response."""
        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)
        
        if self.json_data:
            return jsonify(self.json_data), self.status_code, self.headers
        else:
            return Response(self.body, status=self.status_code, headers=self.headers)


class WebhookServer:
    """Simple webhook server for testing and development."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        debug: bool = False,
        log_requests: bool = True,
        save_requests: bool = False,
        requests_file: Optional[Path] = None,
    ):
        if not FLASK_AVAILABLE:
            raise ImportError("Flask is required for webhook server. Install with: pip install flask")
        
        self.host = host
        self.port = port
        self.debug = debug
        self.log_requests = log_requests
        self.save_requests = save_requests
        self.requests_file = requests_file or Path("webhook_requests.json")
        
        self.app = Flask(__name__)
        self.requests: List[WebhookRequest] = []
        self.handlers: Dict[str, Callable[[WebhookRequest], WebhookResponse]] = {}
        self.default_response = WebhookResponse()
        self._server_thread: Optional[threading.Thread] = None
        self._running = False
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'])
        @self.app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'])
        def catch_all(path):
            webhook_req = WebhookRequest.from_flask_request(request)
            
            # Store request
            self.requests.append(webhook_req)
            
            # Log request
            if self.log_requests:
                print(f"[{webhook_req.timestamp}] {webhook_req.method} {webhook_req.path} - {webhook_req.remote_addr}")
            
            # Save to file
            if self.save_requests:
                self._save_request(webhook_req)
            
            # Find handler
            handler = self.handlers.get(webhook_req.path, None)
            if handler:
                try:
                    response = handler(webhook_req)
                except Exception as e:
                    print(f"Handler error: {e}")
                    response = WebhookResponse(status_code=500, body=f"Handler error: {e}")
            else:
                response = self.default_response
            
            return response.to_flask_response()
        
        @self.app.route('/_admin/requests')
        def admin_requests():
            """Get all captured requests."""
            return jsonify([{
                'id': req.id,
                'timestamp': req.timestamp.isoformat(),
                'method': req.method,
                'path': req.path,
                'headers': req.headers,
                'query_params': req.query_params,
                'body': req.body,
                'json_data': req.json_data,
                'content_type': req.content_type,
                'remote_addr': req.remote_addr,
            } for req in self.requests])
        
        @self.app.route('/_admin/clear', methods=['POST'])
        def admin_clear():
            """Clear all captured requests."""
            self.requests.clear()
            return jsonify({'message': 'Requests cleared'})
    
    def _save_request(self, webhook_req: WebhookRequest):
        """Save request to file."""
        try:
            # Load existing requests
            if self.requests_file.exists():
                with open(self.requests_file, 'r') as f:
                    existing = json.load(f)
            else:
                existing = []
            
            # Add new request
            existing.append({
                'id': webhook_req.id,
                'timestamp': webhook_req.timestamp.isoformat(),
                'method': webhook_req.method,
                'url': webhook_req.url,
                'path': webhook_req.path,
                'headers': webhook_req.headers,
                'query_params': webhook_req.query_params,
                'body': webhook_req.body,
                'json_data': webhook_req.json_data,
                'content_type': webhook_req.content_type,
                'remote_addr': webhook_req.remote_addr,
                'user_agent': webhook_req.user_agent,
            })
            
            # Save back to file
            with open(self.requests_file, 'w') as f:
                json.dump(existing, f, indent=2)
                
        except Exception as e:
            print(f"Failed to save request: {e}")
    
    def add_handler(self, path: str, handler: Callable[[WebhookRequest], WebhookResponse]):
        """Add a custom handler for a specific path."""
        self.handlers[path] = handler
    
    def set_default_response(self, response: WebhookResponse):
        """Set the default response for unhandled requests."""
        self.default_response = response
    
    def start(self, threaded: bool = True) -> None:
        """Start the webhook server."""
        if self._running:
            return
        
        self._running = True
        
        if threaded:
            self._server_thread = threading.Thread(
                target=self._run_server,
                daemon=True
            )
            self._server_thread.start()
            print(f"Webhook server started on http://{self.host}:{self.port}")
        else:
            self._run_server()
    
    def _run_server(self):
        """Run the Flask server."""
        self.app.run(
            host=self.host,
            port=self.port,
            debug=self.debug,
            use_reloader=False,
        )
    
    def stop(self):
        """Stop the webhook server."""
        self._running = False
        if self._server_thread:
            # Note: Flask dev server doesn't have a graceful shutdown
            # In production, you'd use a proper WSGI server
            pass
    
    def get_requests(self) -> List[WebhookRequest]:
        """Get all captured requests."""
        return self.requests.copy()
    
    def clear_requests(self):
        """Clear all captured requests."""
        self.requests.clear()
    
    def wait_for_request(self, timeout: float = 10.0) -> Optional[WebhookRequest]:
        """Wait for the next request."""
        start_count = len(self.requests)
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if len(self.requests) > start_count:
                return self.requests[-1]
            time.sleep(0.1)
        
        return None


# Global server instance for CLI usage
_global_server: Optional[WebhookServer] = None


def start_webhook_server(
    host: str = "localhost",
    port: int = 8080,
    **kwargs
) -> WebhookServer:
    """Start a global webhook server."""
    global _global_server
    
    if _global_server and _global_server._running:
        raise RuntimeError("Webhook server is already running")
    
    _global_server = WebhookServer(host=host, port=port, **kwargs)
    _global_server.start()
    return _global_server


def stop_webhook_server():
    """Stop the global webhook server."""
    global _global_server
    
    if _global_server:
        _global_server.stop()
        _global_server = None


def get_webhook_server() -> Optional[WebhookServer]:
    """Get the global webhook server."""
    return _global_server
