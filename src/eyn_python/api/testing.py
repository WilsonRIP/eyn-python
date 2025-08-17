from __future__ import annotations

import time
import statistics
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
import json

from .client import APIClient, APIResponse, APIError


@dataclass
class TestResult:
    """Result of an API test."""
    name: str
    passed: bool
    message: str
    response: Optional[APIResponse] = None
    execution_time_ms: float = 0.0
    error: Optional[str] = None


@dataclass 
class APITest:
    """Definition of an API test case."""
    name: str
    method: str
    url: str
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, Any]] = None
    json_data: Optional[Dict[str, Any]] = None
    data: Optional[Any] = None
    expected_status: int = 200
    expected_headers: Optional[Dict[str, str]] = None
    expected_json: Optional[Dict[str, Any]] = None
    expected_text: Optional[str] = None
    timeout: Optional[float] = None
    validator: Optional[Callable[[APIResponse], bool]] = None
    description: Optional[str] = None


@dataclass
class APITestSuite:
    """Collection of API tests."""
    name: str
    base_url: str = ""
    default_headers: Dict[str, str] = field(default_factory=dict)
    auth: Optional[Any] = None
    tests: List[APITest] = field(default_factory=list)
    setup: Optional[Callable] = None
    teardown: Optional[Callable] = None
    
    def add_test(self, test: APITest) -> None:
        """Add a test to the suite."""
        self.tests.append(test)
    
    def add_get_test(
        self,
        name: str,
        url: str,
        expected_status: int = 200,
        **kwargs
    ) -> None:
        """Add a GET test."""
        test = APITest(name=name, method='GET', url=url, expected_status=expected_status, **kwargs)
        self.add_test(test)
    
    def add_post_test(
        self,
        name: str,
        url: str,
        json_data: Optional[Dict[str, Any]] = None,
        expected_status: int = 201,
        **kwargs
    ) -> None:
        """Add a POST test."""
        test = APITest(
            name=name,
            method='POST',
            url=url,
            json_data=json_data,
            expected_status=expected_status,
            **kwargs
        )
        self.add_test(test)


def run_single_test(client: APIClient, test: APITest) -> TestResult:
    """Run a single API test."""
    start_time = time.time()
    
    try:
        # Make the request
        response = client.request(
            method=test.method,
            url=test.url,
            headers=test.headers,
            params=test.params,
            json_data=test.json_data,
            data=test.data,
        )
        
        execution_time = (time.time() - start_time) * 1000
        
        # Validate response
        errors = []
        
        # Check status code
        if response.status_code != test.expected_status:
            errors.append(f"Expected status {test.expected_status}, got {response.status_code}")
        
        # Check headers
        if test.expected_headers:
            for key, expected_value in test.expected_headers.items():
                actual_value = response.headers.get(key.lower())
                if actual_value != expected_value:
                    errors.append(f"Expected header {key}: {expected_value}, got: {actual_value}")
        
        # Check JSON response
        if test.expected_json:
            try:
                actual_json = response.json
                if actual_json != test.expected_json:
                    errors.append(f"JSON mismatch. Expected: {test.expected_json}, Got: {actual_json}")
            except Exception as e:
                errors.append(f"Failed to parse JSON: {e}")
        
        # Check text response
        if test.expected_text and test.expected_text not in response.text:
            errors.append(f"Expected text '{test.expected_text}' not found in response")
        
        # Run custom validator
        if test.validator:
            try:
                if not test.validator(response):
                    errors.append("Custom validator failed")
            except Exception as e:
                errors.append(f"Validator error: {e}")
        
        # Return result
        passed = len(errors) == 0
        message = "PASS" if passed else "; ".join(errors)
        
        return TestResult(
            name=test.name,
            passed=passed,
            message=message,
            response=response,
            execution_time_ms=execution_time,
        )
        
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        return TestResult(
            name=test.name,
            passed=False,
            message=f"Test failed with exception: {e}",
            execution_time_ms=execution_time,
            error=str(e),
        )


def run_api_tests(suite: APITestSuite) -> List[TestResult]:
    """Run all tests in a test suite."""
    results = []
    
    # Create client
    client = APIClient(
        base_url=suite.base_url,
        default_headers=suite.default_headers,
        auth=suite.auth,
    )
    
    try:
        # Run setup
        if suite.setup:
            suite.setup()
        
        # Run tests
        for test in suite.tests:
            result = run_single_test(client, test)
            results.append(result)
        
        # Run teardown
        if suite.teardown:
            suite.teardown()
            
    finally:
        client.close()
    
    return results


@dataclass
class BenchmarkResult:
    """Result of API benchmark."""
    url: str
    method: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time_seconds: float
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    median_response_time_ms: float
    requests_per_second: float
    status_codes: Dict[int, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


def benchmark_endpoint(
    client: APIClient,
    method: str,
    url: str,
    requests: int = 100,
    concurrency: int = 10,
    **request_kwargs
) -> BenchmarkResult:
    """Benchmark an API endpoint."""
    import concurrent.futures
    import threading
    
    responses = []
    errors = []
    status_codes = {}
    lock = threading.Lock()
    
    def make_request():
        try:
            response = client.request(method, url, **request_kwargs)
            with lock:
                responses.append(response)
                status_codes[response.status_code] = status_codes.get(response.status_code, 0) + 1
        except Exception as e:
            with lock:
                errors.append(str(e))
    
    # Run benchmark
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(make_request) for _ in range(requests)]
        concurrent.futures.wait(futures)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Calculate statistics
    successful_requests = len(responses)
    failed_requests = len(errors)
    
    if successful_requests > 0:
        response_times = [r.elapsed_ms for r in responses]
        avg_time = statistics.mean(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        median_time = statistics.median(response_times)
    else:
        avg_time = min_time = max_time = median_time = 0.0
    
    rps = requests / total_time if total_time > 0 else 0
    
    return BenchmarkResult(
        url=url,
        method=method,
        total_requests=requests,
        successful_requests=successful_requests,
        failed_requests=failed_requests,
        total_time_seconds=total_time,
        avg_response_time_ms=avg_time,
        min_response_time_ms=min_time,
        max_response_time_ms=max_time,
        median_response_time_ms=median_time,
        requests_per_second=rps,
        status_codes=status_codes,
        errors=errors,
    )


def load_test_suite_from_json(file_path: Path) -> APITestSuite:
    """Load test suite from JSON file."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    suite = APITestSuite(
        name=data.get('name', 'Test Suite'),
        base_url=data.get('base_url', ''),
        default_headers=data.get('default_headers', {}),
    )
    
    for test_data in data.get('tests', []):
        test = APITest(
            name=test_data['name'],
            method=test_data['method'],
            url=test_data['url'],
            headers=test_data.get('headers'),
            params=test_data.get('params'),
            json_data=test_data.get('json_data'),
            data=test_data.get('data'),
            expected_status=test_data.get('expected_status', 200),
            expected_headers=test_data.get('expected_headers'),
            expected_json=test_data.get('expected_json'),
            expected_text=test_data.get('expected_text'),
            description=test_data.get('description'),
        )
        suite.add_test(test)
    
    return suite
