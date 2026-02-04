#!/usr/bin/env python3
"""
High-performance API Proxy with threading and connection pooling.

Features:
- Multi-provider support (gpteamservices, hanbbq)
- Dynamic provider switching via GET /switch/<provider>
- Request format conversion for Responses API
- Thread-safe with Lock protection
- HTTP/1.1 Keep-Alive support
- Rotating log files (10MB limit)

Usage:
    python3 api-proxy.py

Endpoints:
    GET /switch/<provider>  - Switch to specified provider
    GET /status             - Show current provider status
    POST /v1/responses      - Forward to provider (with format conversion for hanbbq)
    POST /v1/*              - Forward to provider
"""
import http.server
import socketserver
import json
import urllib.request
import urllib.error
import ssl
import logging
from logging.handlers import RotatingFileHandler
from threading import Lock

# ===== Configuration =====
PROVIDERS = {
    "gpteamservices": {
        "base": "https://api.gpteamservices.com",
        "key": "sk-83e3fa49d77523d0004dde35ef34f577a8c89f9ebaec8bef",
        "convert": False
    },
    "hanbbq": {
        "base": "https://api.hanbbq.top",
        "key": "sk-831a037edcb8f8d9a0aba15d734785a4",
        "convert": True
    }
}
DEFAULT_PROVIDER = "gpteamservices"
PORT = 4000
LOG_FILE = "/var/log/api-proxy.log"
MAX_LOG_SIZE = 10 * 1024 * 1024
BACKUP_COUNT = 0

# Global state with thread safety
current_provider = DEFAULT_PROVIDER
provider_lock = Lock()

# Reusable SSL context
ssl_ctx = ssl.create_default_context()

# Logging setup
logger = logging.getLogger("api-proxy")
logger.setLevel(logging.INFO)
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT)
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
logger.addHandler(file_handler)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(console_handler)

# Common headers to avoid Cloudflare blocks
COMMON_HEADERS = {
    'User-Agent': 'curl/7.81.0',
    'Accept': '*/*'
}


def convert_to_responses_format(data):
    """Convert messages format to Responses API input format."""
    if 'input' in data and isinstance(data['input'], list):
        if len(data['input']) > 0 and 'content' in data['input'][0]:
            if isinstance(data['input'][0]['content'], list):
                return data

    messages = data.get('messages') or data.get('input', [])
    if not messages:
        return data

    new_input = []
    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')

        if isinstance(content, str):
            content_blocks = [{"type": "input_text", "text": content}]
        elif isinstance(content, list):
            content_blocks = []
            for item in content:
                if isinstance(item, str):
                    content_blocks.append({"type": "input_text", "text": item})
                elif isinstance(item, dict):
                    if 'type' in item and 'text' in item:
                        content_blocks.append(item)
                    elif 'text' in item:
                        content_blocks.append({"type": "input_text", "text": item['text']})
                    else:
                        content_blocks.append(item)
        else:
            content_blocks = [{"type": "input_text", "text": str(content)}]

        new_input.append({"role": role, "content": content_blocks})

    new_data = {k: v for k, v in data.items() if k not in ('messages', 'input')}
    new_data['input'] = new_input
    return new_data


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'  # Enable keep-alive

    def do_POST(self):
        global current_provider

        with provider_lock:
            provider_name = current_provider
        provider = PROVIDERS[provider_name]

        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)

        try:
            req_data = json.loads(body)
            model = req_data.get('model', 'unknown')
            logger.info(f"POST {self.path} | model={model} | provider={provider_name}")

            if provider.get('convert') and self.path == '/v1/responses':
                req_data = convert_to_responses_format(req_data)
                body = json.dumps(req_data).encode()
                logger.info("  -> Converted to Responses API format")
        except Exception as e:
            logger.info(f"POST {self.path} | provider={provider_name} | parse error: {e}")

        target_url = f"{provider['base']}{self.path}"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {provider['key']}",
            **COMMON_HEADERS
        }

        req = urllib.request.Request(target_url, data=body, headers=headers, method='POST')

        try:
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=120) as resp:
                response_body = resp.read()
                self.send_response(resp.status)
                self.send_header('Content-Length', len(response_body))
                for key, value in resp.headers.items():
                    if key.lower() not in ('transfer-encoding', 'connection', 'content-length'):
                        self.send_header(key, value)
                self.end_headers()
                self.wfile.write(response_body)
                logger.info(f"  -> {resp.status} OK ({len(response_body)} bytes)")
        except urllib.error.HTTPError as e:
            err_body = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(err_body))
            self.end_headers()
            self.wfile.write(err_body)
            logger.error(f"  -> {e.code} Error: {err_body[:200]}")
        except Exception as e:
            err_json = json.dumps({'error': str(e)}).encode()
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(err_json))
            self.end_headers()
            self.wfile.write(err_json)
            logger.error(f"  -> 500 Exception: {e}")

    def do_GET(self):
        global current_provider

        if self.path == '/switch':
            with provider_lock:
                resp = {'usage': '/switch/<provider>', 'available': list(PROVIDERS.keys()), 'current': current_provider}
            self._json_response(200, resp)
            return

        if self.path.startswith('/switch/'):
            new_provider = self.path.split('/')[-1].lower()
            if new_provider in PROVIDERS:
                with provider_lock:
                    old = current_provider
                    current_provider = new_provider
                logger.info(f"Switched provider: {old} -> {new_provider}")
                self._json_response(200, {'success': True, 'provider': new_provider, 'base': PROVIDERS[new_provider]['base']})
            else:
                self._json_response(400, {'error': f'Unknown: {new_provider}', 'available': list(PROVIDERS.keys())})
            return

        if self.path == '/status':
            with provider_lock:
                resp = {'current_provider': current_provider, 'base': PROVIDERS[current_provider]['base'], 'available': list(PROVIDERS.keys())}
            self._json_response(200, resp)
            return

        with provider_lock:
            provider_name = current_provider
        provider = PROVIDERS[provider_name]
        target_url = f"{provider['base']}{self.path}"
        logger.info(f"GET {self.path} | provider={provider_name}")

        headers = {'Authorization': f"Bearer {provider['key']}", **COMMON_HEADERS}
        req = urllib.request.Request(target_url, headers=headers, method='GET')

        try:
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=30) as resp:
                response_body = resp.read()
                self.send_response(resp.status)
                self.send_header('Content-Length', len(response_body))
                for key, value in resp.headers.items():
                    if key.lower() not in ('transfer-encoding', 'connection', 'content-length'):
                        self.send_header(key, value)
                self.end_headers()
                self.wfile.write(response_body)
                logger.info(f"  -> {resp.status} OK")
        except urllib.error.HTTPError as e:
            err_body = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(err_body))
            self.end_headers()
            self.wfile.write(err_body)
            logger.error(f"  -> {e.code} Error")

    def _json_response(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == '__main__':
    logger.info(f"API Proxy starting on port {PORT} (threaded)")
    logger.info(f"Default provider: {current_provider} -> {PROVIDERS[current_provider]['base']}")
    logger.info(f"Available providers: {list(PROVIDERS.keys())}")
    server = ThreadedHTTPServer(('0.0.0.0', PORT), ProxyHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.shutdown()
