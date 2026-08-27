"""
Centralized Security & Defense Module for ClawAgent
Implements SSRF Protection, Path Traversal Defense, Secret Redaction,
Payload Size Limits, Input Sanitization, and Resilient JSON Extraction.
"""

import os
import re
import json
import socket
import ipaddress
import urllib.parse
import logging
from typing import Optional, List, Tuple, Set, Any, Dict

logger = logging.getLogger("clawagent.security")

class SecurityException(Exception):
    """Raised when a security validation or policy check fails."""
    pass

# Reserved / Private IP Networks to block for SSRF prevention
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),         # Current network
    ipaddress.ip_network("10.0.0.0/8"),        # Private Class A
    ipaddress.ip_network("100.64.0.0/10"),     # Shared address space (Carrier-grade NAT)
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local / Cloud Metadata (AWS/GCP/Azure)
    ipaddress.ip_network("172.16.0.0/12"),     # Private Class B
    ipaddress.ip_network("192.0.0.0/24"),      # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),      # TEST-NET-1
    ipaddress.ip_network("192.168.0.0/16"),    # Private Class C
    ipaddress.ip_network("198.18.0.0/15"),     # Network benchmark tests
    ipaddress.ip_network("198.51.100.0/24"),   # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),    # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),       # Multicast
    ipaddress.ip_network("240.0.0.0/4"),       # Reserved
    ipaddress.ip_network("255.255.255.255/32"),# Broadcast
    # IPv6
    ipaddress.ip_network("::1/128"),           # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 Unique Local Address
    ipaddress.ip_network("fe80::/10"),         # IPv6 Link-Local
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "instance-data",
    "169.254.169.254"
}

def validate_safe_url(url: str, allowed_schemes: Tuple[str, ...] = ("http", "https")) -> str:
    """
    Validates a URL against SSRF attacks:
    - Verifies protocol is http or https
    - Resolves hostname to IP addresses and checks against private/reserved ranges
    - Rejects cloud metadata and internal loopback domains
    """
    if not url or not isinstance(url, str):
        raise SecurityException("Invalid URL: URL must be a non-empty string.")

    parsed = urllib.parse.urlparse(url.strip())
    if parsed.scheme.lower() not in allowed_schemes:
        raise SecurityException(f"Forbidden URL scheme '{parsed.scheme}'. Only {allowed_schemes} are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise SecurityException(f"Invalid URL: Missing hostname in '{url}'")

    hostname_lower = hostname.lower()
    if hostname_lower in BLOCKED_HOSTNAMES or hostname_lower.endswith(".local") or hostname_lower.endswith(".internal"):
        raise SecurityException(f"Access to internal or restricted hostname '{hostname}' is forbidden.")

    try:
        addr_info = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
        for item in addr_info:
            ip_str = item[4][0]
            ip_obj = ipaddress.ip_address(ip_str)
            for blocked_net in BLOCKED_IP_NETWORKS:
                if ip_obj in blocked_net:
                    raise SecurityException(f"URL resolves to restricted/private IP address: {ip_str}")
    except socket.gaierror as e:
        raise SecurityException(f"Could not resolve hostname '{hostname}': {e}")

    return url.strip()

def validate_safe_file_path(file_path: str, allowed_base_dirs: Optional[List[str]] = None) -> str:
    """
    Validates that a local file path does not escape into sensitive directories.
    Blocks reading .env, system files, or traversing out of project scope.
    """
    if not file_path or not isinstance(file_path, str):
        raise SecurityException("Invalid file path: must be a non-empty string.")

    canonical_path = os.path.realpath(os.path.abspath(file_path))

    basename = os.path.basename(canonical_path).lower()
    if basename in (".env", ".env.local", "secrets.enc", "secrets.json", "id_rsa", "id_ed25519"):
        raise SecurityException(f"Access to sensitive file '{basename}' is strictly forbidden.")

    if allowed_base_dirs:
        matched = False
        for base in allowed_base_dirs:
            real_base = os.path.realpath(os.path.abspath(base))
            if os.path.commonpath([canonical_path, real_base]) == real_base:
                matched = True
                break
        if not matched:
            raise SecurityException(f"Path '{canonical_path}' is outside of permitted directories.")

    return canonical_path

def safe_stream_download(url: str, max_bytes: int = 25 * 1024 * 1024, timeout: int = 15) -> bytes:
    """
    Safely downloads media from a validated URL with strict memory limits and timeouts.
    """
    import requests
    safe_url = validate_safe_url(url)
    
    headers = {
        "User-Agent": "ClawAgent/3.0 (Security-Hardened Bot)"
    }
    
    with requests.get(safe_url, headers=headers, stream=True, timeout=(5, timeout)) as resp:
        resp.raise_for_status()
        
        content_len = resp.headers.get("Content-Length")
        if content_len and int(content_len) > max_bytes:
            raise SecurityException(f"Payload too large: Content-Length {content_len} exceeds max allowed {max_bytes} bytes.")
            
        chunks = []
        total_downloaded = 0
        for chunk in resp.iter_content(chunk_size=64 * 1024):
            if chunk:
                total_downloaded += len(chunk)
                if total_downloaded > max_bytes:
                    raise SecurityException(f"Payload exceeded maximum size limit of {max_bytes} bytes during download.")
                chunks.append(chunk)
                
        return b"".join(chunks)

# Secret Redaction Patterns
SECRET_PATTERNS = [
    (re.compile(r"sk-[a-zA-Z0-9_\-]{20,}", re.IGNORECASE), "sk-***REDACTED***"),
    (re.compile(r"bot[0-9]{8,11}:[a-zA-Z0-9_\-]{30,}", re.IGNORECASE), "bot***REDACTED_TELEGRAM_TOKEN***"),
    (re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE), "Bearer ***REDACTED***"),
    (re.compile(r"key=[a-zA-Z0-9_\-]{20,}", re.IGNORECASE), "key=***REDACTED***"),
    (re.compile(r"api[_-]?key[\"']?\s*[:=]\s*[\"']?[a-zA-Z0-9_\-]{20,}[\"']?", re.IGNORECASE), "api_key=***REDACTED***"),
]

def mask_secrets(text: Optional[str]) -> str:
    if not text:
        return ""
    masked = str(text)
    for pattern, replacement in SECRET_PATTERNS:
        masked = pattern.sub(replacement, masked)
    return masked

def sanitize_handle(handle: str) -> str:
    if not handle:
        raise SecurityException("Handle cannot be empty.")
    clean = handle.strip().lstrip("@")
    if not re.match(r"^[a-zA-Z0-9_.]{1,30}$", clean):
        raise SecurityException(f"Invalid social media handle: '{handle}'. Must be alphanumeric and 1-30 chars.")
    return clean

def sanitize_user_input(text: str, max_length: int = 2000) -> str:
    if not text:
        return ""
    clean = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
    clean = clean.replace("<user_input>", "&lt;user_input&gt;").replace("</user_input>", "&lt;/user_input&gt;")
    return clean[:max_length].strip()

def extract_json_from_llm(raw_text: str) -> Dict[str, Any]:
    """
    Resilient JSON extractor that parses structured objects from LLM outputs,
    handling markdown fences (```json ... ```), preamble text, and trailing commentary.
    """
    if not raw_text or not isinstance(raw_text, str):
        raise ValueError("Empty or invalid response received for JSON extraction.")

    text = raw_text.strip()
    
    # 1. Direct parse attempt
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Extract from markdown code fence
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. Regex search for outermost JSON object or array
    brace_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if brace_match:
        try:
            return json.loads(brace_match.group(1).strip())
        except json.JSONDecodeError:
            # Try cleaning trailing commas before closing braces
            cleaned = re.sub(r",\s*([\}\]])", r"\1", brace_match.group(1))
            return json.loads(cleaned)

    raise ValueError(f"Could not extract valid JSON from LLM output: {raw_text[:200]}")
