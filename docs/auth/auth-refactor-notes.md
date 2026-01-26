# Authentication Refactor

## Problem Statement

Authentication is fragile and the current implementation is a hack, at best.
- [ ] 1. Duplicated Authentication Logic
- [ ] 2. Duplicated Session Objects
- [ ] 3. File-based Token Persistence (Anti-pattern)
- [ ] 4. Scattered 401 retry logic

This has caused unintented results when changing repositories. Because session tokens are scoped to a repository they are intended to be short-lived and destroyed after use. But since the session is writing a JWT to disk, there's a race condition wherein the previous container's images are downloaded, instead of the currently assesed container.

### Current State Analysis

**Problem 1: Duplicated Authentication Logic**

| Location | Implementation |
|----------|----------------|
| [`auth.py:39`](app/modules/auth/auth.py:39) | `fetch_pull_token()` with query string URL |
| [`carver.py:81`](app/modules/keepers/carver.py:81) | `_fetch_pull_token()` - complete duplicate "to avoid circular imports" |
| [`authed-image-config.py:10`](container-image-config/authed-image-config.py:10) | Inline `requests.get()` with params (your simplified approach) |

**Problem 2: Duplicated Session Objects**

| Location | Implementation |
|----------|----------------|
| [`auth.py:5`](app/modules/auth/auth.py:5) | Global `session = requests.Session()` |
| [`carver.py:74`](app/modules/keepers/carver.py:74) | Local `_session = requests.Session()` |

**Problem 3: File-Based Token Persistence (Anti-pattern)**

- [`auth.py:61`](app/modules/auth/auth.py:61) writes to `token_pull.txt`
- [`main.py:140`](main.py:140) reads from `token_pull.txt`

**Problem 4: Scattered 401 Retry Logic** (same pattern in 7+ functions)

- [`downloaders.py`](app/modules/keepers/downloaders.py) - 3 functions
- [`peekers.py`](app/modules/finders/peekers.py) - 4 functions

---

### Solution:

Fix authentication to use a centralized auth module. 

- Create a centralzied authentication module
- See "Proposed Architecture" below for more details.

## Session Invalidator

Session must be destroyed after carving or peeking, to ensure that we're not using the wrong session.

- Add one method to the unified auth class:

```python
def invalidate(self):
    """Kill the session after a peek or carve operation."""
    if self._session:
        self._session.close()
    self._session = None
    self._token = None
```

---

### Proposed Architecture TODO Add - **Add `invalidate()` method** - closes session, clears token into the list below

```
RegistryAuth (one class to rule them all)
├── _token: str
├── _session: requests.Session
├── __init__(namespace, repo)
├── get_session() -> Session with auto-auth
└── _ensure_valid_token() -> auto-refresh on 401
```

Your experimental approach is better because:
1. Uses `params={}` instead of f-string URL (cleaner, handles encoding)
2. No file persistence (tokens are ~5 min TTL anyway)
3. Session-based (bearer token injected once, reused)

---

### Work Breakdown

| Task | Effort | Files |
|------|--------|-------|
| Create `RegistryAuth` class | S | auth.py |
| Add 401 auto-retry middleware | S | auth.py |
| Refactor downloaders.py | S | 1 file, 3 functions |
| Refactor peekers.py | M | 1 file, 4 functions |
| Merge carver.py auth | S | 1 file |
| Refactor layerSlayerResults.py | S | 1 file |
| Update main.py | S | 1 file |
| Remove token_pull.txt persistence | S | cleanup |

---

## Session Invalidator

Add one method to the unified auth class:

```python
def invalidate(self):
    """Kill the session after a peek or carve operation."""
    if self._session:
        self._session.close()
    self._session = None
    self._token = None
```

Call it at the end of [`peek_layer_blob_complete()`](app/modules/finders/peekers.py:56) and [`carve_file()`](app/modules/keepers/carver.py:378) to ensure the session is cleaned up when the operation finishes.

This adds one task to the work breakdown:
- **Add `invalidate()` method** - closes session, clears token


### Risk Factors

- **Circular imports**: carver.py comment explicitly mentions this as why auth was duplicated
- **Token scope**: need to handle per-repo scope (`{namespace}/{repo}:pull`)

---

### Summary

- **6 files** need modification
- **~10 functions** need refactoring  
- Pattern is repetitive and well-understood
