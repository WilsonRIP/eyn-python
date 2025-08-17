from __future__ import annotations

import os
import socket
import subprocess
import ssl
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import threading
import psutil
import dns.resolver
import dns.reversename

from eyn_python.logging import get_logger

log = get_logger(__name__)


def scan_ports(host: str, start_port: int = 1, end_port: int = 1024, 
              timeout: float = 1.0) -> Dict[int, str]:
    """Scan ports on a host."""
    open_ports = {}
    
    for port in range(start_port, end_port + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            if result == 0:
                try:
                    service = socket.getservbyport(port)
                except OSError:
                    service = "unknown"
                open_ports[port] = service
            sock.close()
        except Exception as e:
            log.debug(f"Error scanning port {port}: {e}")
            
    return open_ports


def dns_lookup(domain: str, record_type: str = "A") -> List[str]:
    """Perform DNS lookup."""
    try:
        answers = dns.resolver.resolve(domain, record_type)
        return [str(answer) for answer in answers]
    except Exception as e:
        log.error(f"DNS lookup failed: {e}")
        return []


def reverse_dns_lookup(ip: str) -> Optional[str]:
    """Perform reverse DNS lookup."""
    try:
        addr = dns.reversename.from_address(ip)
        answers = dns.resolver.resolve(addr, "PTR")
        return str(answers[0])
    except Exception as e:
        log.error(f"Reverse DNS lookup failed: {e}")
        return None


def ping_host(host: str, count: int = 4) -> Dict[str, Any]:
    """Ping a host and return statistics."""
    try:
        if os.name == 'nt':  # Windows
            cmd = ['ping', '-n', str(count), host]
        else:  # Unix/Linux
            cmd = ['ping', '-c', str(count), host]
            
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            # Parse ping output (basic parsing)
            lines = result.stdout.split('\n')
            stats = {
                'host': host,
                'reachable': True,
                'packets_sent': count,
                'packets_received': 0,
                'packet_loss': 100.0,
                'min_time': 0,
                'avg_time': 0,
                'max_time': 0,
                'mdev': 0
            }
            
            for line in lines:
                if 'packets transmitted' in line.lower():
                    # Extract packet statistics
                    parts = line.split(',')
                    for part in parts:
                        if 'packets transmitted' in part:
                            stats['packets_sent'] = int(part.split()[0])
                        elif 'received' in part:
                            stats['packets_received'] = int(part.split()[0])
                        elif 'packet loss' in part:
                            loss_str = part.split()[0]
                            stats['packet_loss'] = float(loss_str.replace('%', ''))
                            
                elif 'min/avg/max' in line:
                    # Extract timing statistics
                    parts = line.split('=')[1].strip().split('/')
                    if len(parts) >= 3:
                        stats['min_time'] = float(parts[0])
                        stats['avg_time'] = float(parts[1])
                        stats['max_time'] = float(parts[2])
                        if len(parts) >= 4:
                            stats['mdev'] = float(parts[3])
                            
            return stats
        else:
            return {
                'host': host,
                'reachable': False,
                'error': result.stderr
            }
            
    except subprocess.TimeoutExpired:
        return {
            'host': host,
            'reachable': False,
            'error': 'Timeout'
        }
    except Exception as e:
        return {
            'host': host,
            'reachable': False,
            'error': str(e)
        }


def traceroute(host: str, max_hops: int = 30) -> List[Dict[str, Any]]:
    """Perform traceroute to a host."""
    try:
        if os.name == 'nt':  # Windows
            cmd = ['tracert', '-h', str(max_hops), host]
        else:  # Unix/Linux
            cmd = ['traceroute', '-m', str(max_hops), host]
            
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        hops = []
        lines = result.stdout.split('\n')
        
        for line in lines:
            if line.strip() and not line.startswith('traceroute') and not line.startswith('tracert'):
                # Parse hop information (basic parsing)
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        hop_num = int(parts[0])
                        hop_info = {
                            'hop': hop_num,
                            'host': parts[1] if parts[1] != '*' else None,
                            'ip': None,
                            'time': None
                        }
                        
                        # Extract IP and time if available
                        for part in parts[2:]:
                            if part.replace('.', '').isdigit() and 'ms' not in part:
                                hop_info['ip'] = part
                            elif 'ms' in part:
                                hop_info['time'] = float(part.replace('ms', ''))
                                
                        hops.append(hop_info)
                    except ValueError:
                        continue
                        
        return hops
        
    except Exception as e:
        log.error(f"Traceroute failed: {e}")
        return []


def check_ssl_certificate(host: str, port: int = 443) -> Dict[str, Any]:
    """Check SSL certificate information."""
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                
                if cert is None:
                    return {
                        'host': host,
                        'port': port,
                        'valid': False,
                        'error': 'No certificate found'
                    }
                
                return {
                    'host': host,
                    'port': port,
                    'subject': dict(x[0] for x in cert.get('subject', [])),
                    'issuer': dict(x[0] for x in cert.get('issuer', [])),
                    'version': cert.get('version'),
                    'serial_number': cert.get('serialNumber'),
                    'not_before': cert.get('notBefore'),
                    'not_after': cert.get('notAfter'),
                    'san': cert.get('subjectAltName', []),
                    'valid': True
                }
                
    except Exception as e:
        return {
            'host': host,
            'port': port,
            'valid': False,
            'error': str(e)
        }


def get_whois_info(domain: str) -> Dict[str, Any]:
    """Get WHOIS information for a domain."""
    try:
        if os.name == 'nt':  # Windows
            cmd = ['whois', domain]
        else:  # Unix/Linux
            cmd = ['whois', domain]
            
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return {
                'domain': domain,
                'success': True,
                'data': result.stdout
            }
        else:
            return {
                'domain': domain,
                'success': False,
                'error': result.stderr
            }
            
    except Exception as e:
        return {
            'domain': domain,
            'success': False,
            'error': str(e)
        }


def check_port_status(host: str, port: int, timeout: float = 5.0) -> Dict[str, Any]:
    """Check if a specific port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            try:
                service = socket.getservbyport(port)
            except OSError:
                service = "unknown"
                
            return {
                'host': host,
                'port': port,
                'status': 'open',
                'service': service
            }
        else:
            return {
                'host': host,
                'port': port,
                'status': 'closed'
            }
            
    except Exception as e:
        return {
            'host': host,
            'port': port,
            'status': 'error',
            'error': str(e)
        }


def get_network_interfaces() -> Dict[str, Dict[str, Any]]:
    """Get network interface information."""
    interfaces = {}
    
    for interface, addrs in psutil.net_if_addrs().items():
        interface_info = {
            'name': interface,
            'addresses': [],
            'stats': {}
        }
        
        for addr in addrs:
            interface_info['addresses'].append({
                'family': addr.family,
                'address': addr.address,
                'netmask': addr.netmask,
                'broadcast': addr.broadcast
            })
            
        # Get interface statistics
        try:
            stats = psutil.net_if_stats()[interface]
            interface_info['stats'] = {
                'isup': stats.isup,
                'duplex': stats.duplex.name,
                'speed': stats.speed,
                'mtu': stats.mtu
            }
        except KeyError:
            pass
            
        interfaces[interface] = interface_info
        
    return interfaces


def monitor_bandwidth(duration: int = 60, interval: float = 1.0) -> List[Dict[str, Any]]:
    """Monitor network bandwidth usage."""
    measurements = []
    start_time = time.time()
    
    # Get initial counters
    initial_counters = psutil.net_io_counters()
    
    while time.time() - start_time < duration:
        time.sleep(interval)
        
        # Get current counters
        current_counters = psutil.net_io_counters()
        
        # Calculate differences
        bytes_sent = current_counters.bytes_sent - initial_counters.bytes_sent
        bytes_recv = current_counters.bytes_recv - initial_counters.bytes_recv
        
        # Calculate rates
        elapsed = time.time() - start_time
        send_rate = bytes_sent / elapsed if elapsed > 0 else 0
        recv_rate = bytes_recv / elapsed if elapsed > 0 else 0
        
        measurements.append({
            'timestamp': time.time(),
            'bytes_sent': bytes_sent,
            'bytes_recv': bytes_recv,
            'send_rate_bps': send_rate,
            'recv_rate_bps': recv_rate,
            'send_rate_mbps': send_rate / 1_000_000,
            'recv_rate_mbps': recv_rate / 1_000_000
        })
        
    return measurements


# Import os for platform detection
import os
