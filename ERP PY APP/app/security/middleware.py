import time
from collections import defaultdict
from flask import request, jsonify

class SimpleRateLimiter:
    """In-memory IP rate limiter without Redis dependency."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.hits = defaultdict(list)

    def is_rate_limited(self, ip_address: str) -> bool:
        now = time.time()
        # Filter timestamps within current sliding window
        self.hits[ip_address] = [t for t in self.hits[ip_address] if now - t < self.window_seconds]
        
        if len(self.hits[ip_address]) >= self.max_requests:
            return True

        self.hits[ip_address].append(now)
        return False

# Global instance for sensitive authentication routes
auth_limiter = SimpleRateLimiter(max_requests=5, window_seconds=60)

def rate_limit_auth_middleware():
    """Flask pre-request callback for login endpoints."""
    if request.endpoint == 'auth.login' and request.method == 'POST':
        client_ip = request.remote_addr or '127.0.0.1'
        if auth_limiter.is_rate_limited(client_ip):
            return jsonify({
                "error": "Too many login attempts. Please wait 60 seconds before trying again."
            }), 429