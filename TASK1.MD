# Task  1 auth.py 
This task is in reference to the larger Authentication Refactor detailed [in this doc.](auth-refactor-notes.md)
## 

Task to refactor [auth.py](app\modules\auth\auth.py)

The authentication example below is a highly effective and drastically simplified method to handle the auth. We're going to implement a centralized singluar auth module.

```python
## this is far ore straightforward, compared to what's currently implemented
token = requests.get(
    "https://auth.docker.io/token",
    params={"service": "registry.docker.io", "scope": f"repository:{repo}:pull"},
).json()["token"]

headers = {"Authorization": f"Bearer {token}"}
```

This is drastically simplified and enables us to eliminate the hacky `token_pull.txt` nonsense. It also enables us to rapidly close a session and reauthenticate for a different repository.

 
| Task | Effort | Files |
|------|--------|-------|
| Create `RegistryAuth` class | S | auth.py |
| Add 401 auto-retry middleware | S | auth.py |
| Add `invalidate()` method - closes session, clears token |  S | auth.py |

## Session Invalidator

- Add one method to the unified auth class:

```python
def invalidate(self):
    """Kill the session after a peek or carve operation."""
    if self._session:
        self._session.close()
    self._session = None
    self._token = None
```

- Call it at the end of [`peek_layer_blob_complete()`](app/modules/finders/peekers.py:56) and [`carve_file()`](app/modules/keepers/carver.py:378) to ensure the session is cleaned up when the operation finishes.

Task: Refactor auth.py:
    - Code is tested in `authed-mage-config.py`. Now that the concept is proven, it's time to rip out the old auth code and replace it with this module. 