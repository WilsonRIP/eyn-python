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


# ---------- Helpers ----------
def _safe_str(v: object) -> str:
    try:
        return str(v)
    except Exception:
        return "<unrepresentable>"


def _cert_name_to_dict(name_tuple: Any) -> Dict[str, str]:
    """
    Convert certificate subject/issuer structure returned by ssl.getpeercert()
    into a simple dict: { 'commonName': 'example.com', ... }
    The structure is commonly: ((('commonName', 'example.com'),), (('countryName','US'),), ...)
    """
    out: Dict[str, str] = {}
    if not name_tuple:
        return out

    # Handle different possible types from SSL certificate
    if isinstance(name_tuple, (list, tuple)):
        for rdn in name_tuple:
            # rdn often is a tuple containing one or more tuples
            if isinstance(rdn, (list, tuple)):
                for entry in rdn:
                    if isinstance(entry, (list, tuple)) and len(entry) >= 2:
                        key = _safe_str(entry[0])
                        val = _safe_str(entry[1])
                        # If a key appears more than once, later ones override earlier
                        out[key] = val
    return out


# ---------- Network utilities ----------
def scan_ports(host: str, start_port: int = 1, end_port: int = 1024, timeout: float = 1.0) -> Dict[int, str]:
    """Scan ports on a host (TCP). Returns mapping port -> service (or 'unknown')."""
    open_ports: Dict[int, str] = {}

    for port in range(start_port, end_port + 1):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            if result == 0:
                try:
                    # May raise OSError for unknown ports
                    service = socket.getservbyport(port)
                except OSError:
                    service = "unknown"
                open_ports[port] = service
        except Exception as e:
            log.debug("Error scanning port %s:%d -> %s", host, port, e)
        finally:
            try:
                sock.close()
            except Exception:
                pass

    return open_ports


def dns_lookup(domain: str, record_type: str = "A") -> List[str]:
    """Perform DNS lookup for a given record type. Returns list of results as strings."""
    try:
        answers = dns.resolver.resolve(domain, record_type)
        return [str(rdata) for rdata in answers]
    except Exception as e:
        log.error("DNS lookup failed for %s (%s): %s", domain, record_type, e)
        return []


def reverse_dns_lookup(ip: str) -> Optional[str]:
    """Perform reverse DNS lookup (PTR). Returns hostname or None."""
    try:
        addr = dns.reversename.from_address(ip)
        answers = dns.resolver.resolve(addr, "PTR")
        return str(answers[0]).rstrip('.')  # strip trailing dot
    except Exception as e:
        log.error("Reverse DNS lookup failed for %s: %s", ip, e)
        return None


def ping_host(host: str, count: int = 4) -> Dict[str, Any]:
    """
    Ping a host and return basic statistics.
    Works on both Windows and Unix-like OSes (parses common output formats).
    """
    try:
        if os.name == "nt":
            cmd = ["ping", "-n", str(count), host]
        else:
            cmd = ["ping", "-c", str(count), host]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        stdout = result.stdout or ""
        stderr = result.stderr or ""

        base_stats: Dict[str, Any] = {
            "host": host,
            "reachable": False,
            "packets_sent": count,
            "packets_received": 0,
            "packet_loss": 100.0,
            "min_time": None,
            "avg_time": None,
            "max_time": None,
            "mdev": None,
            "raw": stdout,
        }

        if result.returncode != 0 and not stdout:
            # no useful stdout, return error
            return {
                "host": host,
                "reachable": False,
                "error": stderr or "ping failed"
            }

        text = stdout.splitlines()
        # Try linux/mac style first
        for line in text:
            lower = line.lower()
            if "packets transmitted" in lower or "packets transmitted" in line:
                # linux style: "4 packets transmitted, 4 received, 0% packet loss, time 3067ms"
                parts = [p.strip() for p in line.split(",")]
                for part in parts:
                    if "packets transmitted" in part:
                        try:
                            base_stats["packets_sent"] = int(part.split()[0])
                        except Exception:
                            pass
                    elif "received" in part and "%" not in part:
                        try:
                            base_stats["packets_received"] = int(part.split()[0])
                        except Exception:
                            pass
                    elif "packet loss" in part or "loss" in part:
                        try:
                            loss_str = part.split()[0].replace("%", "")
                            base_stats["packet_loss"] = float(loss_str)
                            base_stats["reachable"] = base_stats["packet_loss"] < 100.0
                        except Exception:
                            pass
            # linux timing: "rtt min/avg/max/mdev = 0.025/0.025/0.025/0.000 ms"
            if "min/avg/max" in lower or "rtt min/avg/max" in lower or "round-trip min/avg/max" in lower:
                try:
                    if "=" in line:
                        vals = line.split("=")[1].strip().split()[0]  # "0.025/0.025/0.025/0.000"
                        parts = vals.split("/")
                        if len(parts) >= 3:
                            base_stats["min_time"] = float(parts[0])
                            base_stats["avg_time"] = float(parts[1])
                            base_stats["max_time"] = float(parts[2])
                        if len(parts) >= 4:
                            base_stats["mdev"] = float(parts[3])
                except Exception:
                    pass

        # Windows parsing fallback
        if os.name == "nt":
            for line in text:
                if "packets: sent" in line.lower() or "packets:" in line.lower() and "sent =" in line.lower():
                    # Example: "    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),"
                    try:
                        # crude parse:
                        items = line.replace(",", "").replace("(", "").replace(")", "").split()
                        # find numeric tokens by label
                        for i, token in enumerate(items):
                            if token.lower().startswith("sent"):
                                base_stats["packets_sent"] = int(items[i + 2])
                            elif token.lower().startswith("received"):
                                base_stats["packets_received"] = int(items[i + 2])
                            elif token.lower().startswith("lost"):
                                # next token is count
                                lost = int(items[i + 2])
                                # compute loss percent if possible
                        # try to find "(0% loss)" style in the line
                        if "%" in line:
                            try:
                                pct = float(line.split("%")[0].split()[-1].replace("(", ""))
                                base_stats["packet_loss"] = pct
                                base_stats["reachable"] = pct < 100.0
                            except Exception:
                                pass
                    except Exception:
                        pass
                # Windows timing: "Minimum = 0ms, Maximum = 1ms, Average = 0ms"
                if "minimum =" in line.lower() or "average =" in line.lower():
                    try:
                        # collect tokens like Minimum = 0ms,
                        toks = line.replace(",", "").split()
                        # map words to values
                        for i, t in enumerate(toks):
                            if t.lower().startswith("minimum") and i + 2 < len(toks):
                                base_stats["min_time"] = float(toks[i + 2].replace("ms", ""))
                            elif t.lower().startswith("maximum") and i + 2 < len(toks):
                                base_stats["max_time"] = float(toks[i + 2].replace("ms", ""))
                            elif t.lower().startswith("average") and i + 2 < len(toks):
                                base_stats["avg_time"] = float(toks[i + 2].replace("ms", ""))
                    except Exception:
                        pass

        # If we got any received packets, mark reachable
        try:
            if base_stats["packets_received"] and int(base_stats["packets_received"]) > 0:
                base_stats["reachable"] = True
                if base_stats["packets_sent"]:
                    base_stats["packet_loss"] = round(
                        (1 - (int(base_stats["packets_received"]) / int(base_stats["packets_sent"]))) * 100, 2
                    )
        except Exception:
            pass

        return base_stats

    except subprocess.TimeoutExpired:
        return {"host": host, "reachable": False, "error": "Timeout"}
    except Exception as e:
        return {"host": host, "reachable": False, "error": str(e)}


def traceroute(host: str, max_hops: int = 30) -> List[Dict[str, Any]]:
    """
    Perform a traceroute (Unix: traceroute, Windows: tracert).
    Returns a list of hops: [{'hop': n, 'host': host_or_none, 'ip': ip_or_none, 'times': [..]}]
    """
    try:
        if os.name == "nt":
            cmd = ["tracert", "-h", str(max_hops), host]
        else:
            cmd = ["traceroute", "-m", str(max_hops), host]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        lines = (result.stdout or "").splitlines()
        hops: List[Dict[str, Any]] = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Skip header line(s)
            if line.lower().startswith("traceroute") or line.lower().startswith("tracert"):
                continue

            parts = line.split()
            # First token often the hop number
            try:
                hop_num = int(parts[0])
            except Exception:
                continue

            hop_entry: Dict[str, Any] = {"hop": hop_num, "host": None, "ip": None, "times": []}

            # Try to find an IP in parentheses: "example.com (1.2.3.4)"
            if "(" in line and ")" in line:
                try:
                    ip_candidate = line[line.find("(") + 1: line.find(")")]
                    hop_entry["ip"] = ip_candidate
                    # host is the token before '('
                    pre = line[: line.find("(")].strip().split()
                    if len(pre) >= 2:
                        hop_entry["host"] = pre[1]
                except Exception:
                    pass
            else:
                # fallback: second token could be hostname or '*'
                if len(parts) >= 2 and parts[1] != "*":
                    hop_entry["host"] = parts[1]

                # sometimes IPs appear as the third token
                for p in parts[2:]:
                    if p and all(ch.isdigit() or ch == "." for ch in p):
                        hop_entry["ip"] = p
                        break

            # extract timing values like "  1.123 ms" or "  1 ms"
            for token in parts:
                if token.endswith("ms"):
                    try:
                        hop_entry["times"].append(float(token.replace("ms", "")))
                    except Exception:
                        pass
                else:
                    # tokens like '1.123' followed by 'ms' separated (rare)
                    pass

            hops.append(hop_entry)
        return hops

    except Exception as e:
        log.error("Traceroute failed for %s: %s", host, e)
        return []


def check_ssl_certificate(host: str, port: int = 443) -> Dict[str, Any]:
    """
    Connect to host:port and return parsed certificate information.
    """
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                if not cert:
                    return {"host": host, "port": port, "valid": False, "error": "No certificate found"}

                subject = _cert_name_to_dict(cert.get("subject", ()))
                issuer = _cert_name_to_dict(cert.get("issuer", ()))

                return {
                    "host": host,
                    "port": port,
                    "subject": subject,
                    "issuer": issuer,
                    "version": cert.get("version"),
                    "serial_number": cert.get("serialNumber") or cert.get("serial_number"),
                    "not_before": cert.get("notBefore"),
                    "not_after": cert.get("notAfter"),
                    "san": cert.get("subjectAltName", []),
                    "valid": True,
                }

    except Exception as e:
        return {"host": host, "port": port, "valid": False, "error": str(e)}


def get_whois_info(domain: str) -> Dict[str, Any]:
    """Get WHOIS information for a domain using the `whois` command if available."""
    try:
        cmd = ["whois", domain]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return {"domain": domain, "success": True, "data": result.stdout}
        else:
            return {"domain": domain, "success": False, "error": result.stderr or result.stdout}

    except FileNotFoundError:
        return {"domain": domain, "success": False, "error": "whois command not available"}
    except Exception as e:
        return {"domain": domain, "success": False, "error": str(e)}


def check_port_status(host: str, port: int, timeout: float = 5.0) -> Dict[str, Any]:
    """Return whether a TCP port is open on a host, and reported service when open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
        finally:
            try:
                sock.close()
            except Exception:
                pass

        if result == 0:
            try:
                service = socket.getservbyport(port)
            except OSError:
                service = "unknown"
            return {"host": host, "port": port, "status": "open", "service": service}
        else:
            return {"host": host, "port": port, "status": "closed"}

    except Exception as e:
        return {"host": host, "port": port, "status": "error", "error": str(e)}


def get_network_interfaces() -> Dict[str, Dict[str, Any]]:
    """Return network interface addresses and stats using psutil."""
    interfaces: Dict[str, Dict[str, Any]] = {}

    # duplex mapping: 0 unknown, 1 half, 2 full (psutil uses ints)
    duplex_map = {
        getattr(psutil, "NIC_DUPLEX_UNKNOWN", 0): "unknown",
        getattr(psutil, "NIC_DUPLEX_HALF", 1): "half",
        getattr(psutil, "NIC_DUPLEX_FULL", 2): "full",
    }

    for interface, addrs in psutil.net_if_addrs().items():
        interface_info: Dict[str, Any] = {"name": interface, "addresses": [], "stats": {}}

        for addr in addrs:
            try:
                interface_info["addresses"].append({
                    "family": getattr(addr, "family", None),
                    "address": getattr(addr, "address", None),
                    "netmask": getattr(addr, "netmask", None),
                    "broadcast": getattr(addr, "broadcast", None)
                })
            except Exception:
                # fallback in case of unexpected structure
                interface_info["addresses"].append({"raw": _safe_str(addr)})

        # Get interface statistics
        try:
            stats = psutil.net_if_stats()[interface]
            duplex_val = getattr(stats, "duplex", None)
            interface_info["stats"] = {
                "isup": getattr(stats, "isup", None),
                "duplex": duplex_map.get(duplex_val, _safe_str(duplex_val)),
                "speed": getattr(stats, "speed", None),
                "mtu": getattr(stats, "mtu", None),
            }
        except KeyError:
            # leave stats empty
            pass

        interfaces[interface] = interface_info

    return interfaces


def monitor_bandwidth(duration: int = 60, interval: float = 1.0) -> List[Dict[str, Any]]:
    """
    Monitor network I/O over `duration` seconds with `interval` samples.
    Returns a list of measurement dicts with send/recv totals and rates (bps).
    """
    measurements: List[Dict[str, Any]] = []
    start_time = time.time()
    initial_counters = psutil.net_io_counters()

    while time.time() - start_time < duration:
        time.sleep(interval)
        current_counters = psutil.net_io_counters()

        elapsed = time.time() - start_time
        bytes_sent = current_counters.bytes_sent - initial_counters.bytes_sent
        bytes_recv = current_counters.bytes_recv - initial_counters.bytes_recv

        send_rate = bytes_sent / elapsed if elapsed > 0 else 0.0
        recv_rate = bytes_recv / elapsed if elapsed > 0 else 0.0

        measurements.append({
            "timestamp": time.time(),
            "bytes_sent": bytes_sent,
            "bytes_recv": bytes_recv,
            "send_rate_bps": send_rate,
            "recv_rate_bps": recv_rate,
            "send_rate_mbps": send_rate / 1_000_000,
            "recv_rate_mbps": recv_rate / 1_000_000,
        })

    return measurements
