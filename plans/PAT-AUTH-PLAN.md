# PAT Authentication Implementation Plan

## Goal
Add personal access token (PAT) authentication to `app/modules/auth/auth.py` for authenticated rate limits (200 pulls vs 100 anonymous).

## Current State
- [`RegistryAuth._fetch_token()`](../app/modules/auth/auth.py:40) calls `auth.docker.io/token` with no credentials
- Returns anonymous token

## Implementation

### 1. Create `app/config.py`

```python
"""
Docker Hub credentials for authenticated rate limits.
Leave empty for anonymous access.
"""

DOCKERHUB_IDENTIFIER = ""  # Docker Hub username
DOCKERHUB_SECRET = ""       # PAT or password
```

### 2. Modify `app/modules/auth/auth.py`

In [`_fetch_token()`](../app/modules/auth/auth.py:40), add auth parameter:

```python
from app.config import DOCKERHUB_IDENTIFIER, DOCKERHUB_SECRET

def _fetch_token(self) -> str:
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
    # ... rest unchanged
```

## What Does NOT Change
- No new classes
- No environment variables
- `get_session()`, `request_with_retry()`, `invalidate()` unchanged
- Empty config = anonymous access (current behavior)
