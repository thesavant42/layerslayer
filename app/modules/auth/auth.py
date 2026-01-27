"""
Centralized Docker registry authentication.

Provides RegistryAuth class for all registry API calls with:
- Token auto-refresh on 401
- Session management
- Proper cleanup via invalidate()
"""

import requests
from typing import Optional

from app.config import DOCKERHUB_IDENTIFIER, DOCKERHUB_SECRET


class RegistryAuth:
    """
    Centralized Docker registry authentication.
    
    Usage:
        auth = RegistryAuth("library", "nginx")
        resp = auth.request_with_retry("GET", url)
        # ... do work ...
        auth.invalidate()  # cleanup when done
    """
    
    AUTH_URL = "https://auth.docker.io/token"
    
    def __init__(self, namespace: str, repo: str):
        """
        Initialize auth for a specific repository.
        
        Args:
            namespace: Docker Hub namespace (e.g., "library", "nginx")
            repo: Repository name (e.g., "nginx", "alpine")
        """
        self.namespace = namespace
        self.repo = repo
        self._token: Optional[str] = None
        self._session: Optional[requests.Session] = None
    
    def _fetch_token(self) -> str:
        """
        Fetch a fresh pull token.
        
        Uses params dict approach (cleaner than f-string URL, handles encoding).
        If credentials are configured, uses authenticated request for higher rate limits.
        """
        auth = None
        if DOCKERHUB_IDENTIFIER and DOCKERHUB_SECRET:
            auth = (DOCKERHUB_IDENTIFIER, DOCKERHUB_SECRET)
        
        resp = requests.get(
            self.AUTH_URL,
            params={
                "service": "registry.docker.io",
                "scope": f"repository:{self.namespace}/{self.repo}:pull"
            },
            auth=auth,
            timeout=10
        )
        resp.raise_for_status()
        token = resp.json().get("token")
        if not token:
            raise ValueError("Auth endpoint returned no token")
        return token
    
    def _ensure_valid_token(self) -> str:
        """Get token, fetching if not cached."""
        if not self._token:
            self._token = self._fetch_token()
        return self._token
    
    def get_session(self) -> requests.Session:
        """
        Get authenticated session.
        
        Creates session on first call, reuses thereafter.
        Token is injected into Authorization header.
        """
        if not self._session:
            self._session = requests.Session()
            self._session.headers.update({
                "Accept": "application/vnd.docker.distribution.manifest.v2+json, "
                          "application/vnd.oci.image.manifest.v1+json"
            })
        
        token = self._ensure_valid_token()
        self._session.headers["Authorization"] = f"Bearer {token}"
        return self._session
    
    def request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request with automatic 401 retry.
        
        On 401 response, refreshes token and retries once.
        
        Args:
            method: HTTP method ("GET", "HEAD", etc.)
            url: Full URL to request
            **kwargs: Passed to requests (e.g., stream=True, timeout=30)
            
        Returns:
            requests.Response object
        """
        session = self.get_session()
        resp = session.request(method, url, **kwargs)
        
        if resp.status_code == 401:
            # Token expired or invalid, refresh and retry once
            self._token = None
            session = self.get_session()
            resp = session.request(method, url, **kwargs)
        
        return resp
    
    def invalidate(self):
        """
        Kill session after peek/carve operation.
        
        Call this at operation boundaries to ensure tokens scoped
        to one repository are not accidentally reused for another.
        """
        if self._session:
            self._session.close()
        self._session = None
        self._token = None


# Convenience function for simple one-off requests
def get_auth(namespace: str, repo: str) -> RegistryAuth:
    """Factory function to create a RegistryAuth instance."""
    return RegistryAuth(namespace, repo)
