from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import httpx
from urllib.parse import urljoin, urlparse


@dataclass
class APIResponse:
    """Response from an API call."""
    status_code: int
    headers: Dict[str, str]
    text: str
    url: str
    elapsed_ms: float
    request_method: str
    request_headers: Dict[str, str]
    request_body: Optional[str] = None
    
    @property
    def json(self) -> Any:
        """Parse response as JSON."""
        try:
            return json.loads(self.text)
        except json.JSONDecodeError:
            return None
    
    @property
    def ok(self) -> bool:
        """Check if request was successful (2xx status)."""
        return 200 <= self.status_code < 300
    
    @property
    def content_type(self) -> str:
        """Get content type from headers."""
        return self.headers.get('content-type', '').split(';')[0].strip()


class APIError(Exception):
    """Exception raised for API errors."""
    def __init__(self, message: str, response: Optional[APIResponse] = None):
        super().__init__(message)
        self.response = response


class AuthMethod(ABC):
    """Base class for authentication methods."""
    
    @abstractmethod
    def apply(self, headers: Dict[str, str]) -> None:
        """Apply authentication to request headers."""
        pass


@dataclass
class BearerAuth(AuthMethod):
    """Bearer token authentication."""
    token: str
    
    def apply(self, headers: Dict[str, str]) -> None:
        headers['Authorization'] = f'Bearer {self.token}'


@dataclass
class BasicAuth(AuthMethod):
    """HTTP Basic authentication."""
    username: str
    password: str
    
    def apply(self, headers: Dict[str, str]) -> None:
        import base64
        credentials = base64.b64encode(f'{self.username}:{self.password}'.encode()).decode()
        headers['Authorization'] = f'Basic {credentials}'


@dataclass 
class APIKeyAuth(AuthMethod):
    """API key authentication."""
    key: str
    header_name: str = 'X-API-Key'
    
    def apply(self, headers: Dict[str, str]) -> None:
        headers[self.header_name] = self.key


@dataclass
class CustomHeaderAuth(AuthMethod):
    """Custom header authentication."""
    headers: Dict[str, str]
    
    def apply(self, headers: Dict[str, str]) -> None:
        headers.update(self.headers)


@dataclass
class APIClient:
    """HTTP client for API testing and interaction."""
    base_url: str = ""
    default_headers: Dict[str, str] = field(default_factory=dict)
    auth: Optional[AuthMethod] = None
    timeout: float = 30.0
    verify_ssl: bool = True
    follow_redirects: bool = True
    
    def __post_init__(self):
        self._client = None
    
    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout,
                verify=self.verify_ssl,
                follow_redirects=self.follow_redirects,
            )
        return self._client
    
    def _prepare_url(self, url: str) -> str:
        """Prepare full URL from base URL and endpoint."""
        if url.startswith(('http://', 'https://')):
            return url
        return urljoin(self.base_url.rstrip('/') + '/', url.lstrip('/'))
    
    def _prepare_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Prepare request headers with defaults and auth."""
        final_headers = self.default_headers.copy()
        if headers:
            final_headers.update(headers)
        
        if self.auth:
            self.auth.apply(final_headers)
        
        return final_headers
    
    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes, Dict[str, Any]]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> APIResponse:
        """Make HTTP request and return APIResponse."""
        full_url = self._prepare_url(url)
        request_headers = self._prepare_headers(headers)
        
        # Prepare request body
        request_body = None
        if json_data is not None:
            request_body = json.dumps(json_data)
            request_headers.setdefault('Content-Type', 'application/json')
        elif isinstance(data, (dict, list)):
            request_body = json.dumps(data)
            request_headers.setdefault('Content-Type', 'application/json')
        elif data is not None:
            request_body = str(data)
        
        start_time = time.time()
        
        try:
            response = self.client.request(
                method=method.upper(),
                url=full_url,
                headers=request_headers,
                params=params,
                json=json_data,
                data=data if json_data is None else None,
                files=files,
            )
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            return APIResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                text=response.text,
                url=str(response.url),
                elapsed_ms=elapsed_ms,
                request_method=method.upper(),
                request_headers=request_headers,
                request_body=request_body,
            )
            
        except httpx.RequestError as e:
            raise APIError(f"Request failed: {e}")
    
    def get(self, url: str, **kwargs) -> APIResponse:
        """Make GET request."""
        return self.request('GET', url, **kwargs)
    
    def post(self, url: str, **kwargs) -> APIResponse:
        """Make POST request."""
        return self.request('POST', url, **kwargs)
    
    def put(self, url: str, **kwargs) -> APIResponse:
        """Make PUT request."""
        return self.request('PUT', url, **kwargs)
    
    def patch(self, url: str, **kwargs) -> APIResponse:
        """Make PATCH request."""
        return self.request('PATCH', url, **kwargs)
    
    def delete(self, url: str, **kwargs) -> APIResponse:
        """Make DELETE request."""
        return self.request('DELETE', url, **kwargs)
    
    def head(self, url: str, **kwargs) -> APIResponse:
        """Make HEAD request."""
        return self.request('HEAD', url, **kwargs)
    
    def options(self, url: str, **kwargs) -> APIResponse:
        """Make OPTIONS request."""
        return self.request('OPTIONS', url, **kwargs)
    
    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def quick_request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    **kwargs
) -> APIResponse:
    """Make a quick HTTP request without creating a client."""
    with APIClient() as client:
        return client.request(method, url, headers=headers, **kwargs)


def get(url: str, **kwargs) -> APIResponse:
    """Quick GET request."""
    return quick_request('GET', url, **kwargs)


def post(url: str, **kwargs) -> APIResponse:
    """Quick POST request."""
    return quick_request('POST', url, **kwargs)


def put(url: str, **kwargs) -> APIResponse:
    """Quick PUT request."""
    return quick_request('PUT', url, **kwargs)


def delete(url: str, **kwargs) -> APIResponse:
    """Quick DELETE request."""
    return quick_request('DELETE', url, **kwargs)
