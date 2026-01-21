# Authentication Refactor - Implementation Plan

## Overview

All-at-once refactor on a feature branch. Changes auth.py and all consumers together.

---

## 1. New RegistryAuth Class Design

```python
# app/modules/auth/auth.py

import requests
from typing import Optional

class RegistryAuth:
    """Centralized Docker registry authentication."""
    
    AUTH_URL = "https://auth.docker.io/token"
    
    def __init__(self, namespace: str, repo: str):
        self.namespace = namespace
        self.repo = repo
        self._token: Optional[str] = None
        self._session: Optional[requests.Session] = None
    
    def _fetch_token(self) -> str:
        """Fetch a fresh pull token using params dict approach."""
        resp = requests.get(
            self.AUTH_URL,
            params={
                "service": "registry.docker.io",
                "scope": f"repository:{self.namespace}/{self.repo}:pull"
            },
            timeout=10
        )
        resp.raise_for_status()
        return resp.json()["token"]
    
    def _ensure_valid_token(self) -> str:
        """Get token, refreshing if needed."""
        if not self._token:
            self._token = self._fetch_token()
        return self._token
    
    def get_session(self) -> requests.Session:
        """Get authenticated session with auto-retry on 401."""
        if not self._session:
            self._session = requests.Session()
            self._session.headers.update({
                "Accept": "application/vnd.docker.distribution.manifest.v2+json, "
                          "application/vnd.oci.image.manifest.v1+json"
            })
        
        token = self._ensure_valid_token()
        self._session.headers["Authorization"] = f"Bearer {token}"
        return self._session
    
    def request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make request with automatic 401 retry."""
        session = self.get_session()
        resp = session.request(method, url, **kwargs)
        
        if resp.status_code == 401:
            # Token expired, refresh and retry once
            self._token = None
            session = self.get_session()
            resp = session.request(method, url, **kwargs)
        
        return resp
    
    def invalidate(self):
        """Kill session after peek/carve operation."""
        if self._session:
            self._session.close()
        self._session = None
        self._token = None
```

---

## 2. Consumer Changes

### 2.1 carver.py

**Remove:**
- Lines 74-93: `_session` and `_fetch_pull_token()` 

**Add:**
- Import: `from app.modules.auth import RegistryAuth`
- Create auth instance in `carve_file()`: `auth = RegistryAuth(namespace, repo)`
- Replace `_session.get()` calls with `auth.request_with_retry()`
- Add `auth.invalidate()` at end of `carve_file()`

### 2.2 peekers.py

**Current pattern repeated in 4 functions:**
```python
resp = session.get(url, headers=auth_headers(token))
if resp.status_code == 401:
    token = fetch_pull_token(...)
    resp = session.get(url, headers=auth_headers(token))
```

**New pattern:**
```python
auth = RegistryAuth(namespace, repo)
resp = auth.request_with_retry("GET", url)
```

**Add `auth.invalidate()` at end of `peek_layer_blob_complete()`**

### 2.3 downloaders.py

Same pattern change as peekers.py for 3 functions.

### 2.4 layerSlayerResults.py

Update to use RegistryAuth if it has auth logic.

### 2.5 main.py

**Remove:**
- Reading from `token_pull.txt`
- Any token file handling

**Update:**
- Pass RegistryAuth instance or namespace/repo to functions that need auth

---

## 3. Files to Delete/Clean

- Remove `token_pull.txt` if it exists in repo
- Remove `save_token()` and `load_token()` functions from auth.py
- Remove old `fetch_pull_token()` function from auth.py
- Remove global `session` from auth.py

---

## 4. Execution Order

Since this is all-at-once on a branch:

1. Create feature branch
2. Rewrite auth.py with RegistryAuth class
3. Update carver.py
4. Update peekers.py  
5. Update downloaders.py
6. Update layerSlayerResults.py
7. Update main.py
8. Delete deprecated code and token file
9. Run tests / manual verification
10. Merge to main

---

## 5. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Circular imports | RegistryAuth has no dependencies on other app modules |
| Token scope mismatch | Each RegistryAuth instance is scoped to namespace/repo |
| Session leaks | `invalidate()` called at operation boundaries |
| Breaking existing flows | Test each entry point: main.py CLI, carver.py CLI, API endpoints |

---

## 6. Test Checklist

- [ ] `python main.py -t nginx:alpine --peek-all` works
- [ ] `python -m app.modules.keepers.carver ubuntu:24.04 /etc/passwd` works
- [ ] Switching images mid-session does not cause cross-repo contamination
- [ ] API endpoints in app/modules/api/ work correctly
