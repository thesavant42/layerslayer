# Git Commit Breaks Docker Hub Search Sorting

## Probem Statement:
- commit: `105157435e0ffcc2ee3eb9efaaa63a1a3b276b89`  broke `search_dockerhub.ppy`,
    -  no longer utilizes the ordering and sorting parameters.
- Logic is truthy; it gets valid json responses but they do not change when sort parameters change.

## Impact
- Can't page through results by most recently updated
- Can't resort in the UI

Textual TUI is [/app/tui/app.py](/app/tui/app.py) - Out of scope for this test; the API needs to work *first*

Docker Hub Search is different than the other Docker Hub routes; it's reverse engineered from the undocumented protocol, and worked prior to the offending git commit.


---

## Facts
- Prior to commit: `105157435e0ffcc2ee3eb9efaaa63a1a3b276b89` search worked the way it was supposed to. 
    - Default of `30` results per page,
    - Order by `Last Updated` time, `Desc`.

- Then this change, which alledges to only pass through json response, broke it.

---

## Proof:
- The Docker Hub Search API is handled by `/app/modules/search/search_dockerhub.py`
- It's a passthrough API, and will return passthrough results from `http://127.0.0.1:8000/search.data?q=disney&page=1&sortby=updated_at&order=asc` (ascending sort)
and `http://127.0.0.1:8000/search.data?q=disney&page=1&sortby=updated_at&order=desc` (descending sort) **should return different results,** but they are *exactly the same*. 
    - Unsorted.
    - Not ordered.

---

### Theory
- This happens because with no additional parameters, the docker hub api returns the most popular results.
- This commit obviously made assumptions about how the `/app/modules/search/search_dockerhub.py` app.
- Problem: The JSON results returned by the API are NOT passthrough from Docker Hub,
    -  they are completely reformatted.
    - Not parsing the pagination responses with pagination glyph

- GET `http://127.0.0.1:8000/search.data?q=disney&page=1&sortby=updated_at&order=desc` SHOULD return the same exact json as 
- GET `https://hub.docker.com/search.data?q=disney&page=1&sortby=updated_at&order=desc`


---
## Background
The purpose of [/app/modules/search/search_dockerhub.py](/app/modules/search/search_dockerhub.py) is to parse that json;

[plans/dockerhubsearch.md](plans/dockerhubsearch.md) - Reverse engineering notes from dockerhub JSON

https://hub.docker.com/search.data?q=disney&page=1&sortby=updated_at&order=desc
https://hub.docker.com/search.data?q=disney&page=1&sortby=updated_at&order=asc


---

## Task:
- Fix the bug so that

### Acceptance Criteria:
- [ ] 1. `desc`: A request to - GET `http://127.0.0.1:8000/search.data?q=disney&page=1&sortby=updated_at&order=desc` returns the same *exact* json as  GET `https://hub.docker.com/search.data?q=disney&page=1&sortby=updated_at&order=desc`
- [ ] 2. `asc`:  A Request to - GET `http://127.0.0.1:8000/search.data?q=disney&page=1&sortby=updated_at&order=asc` returns the same *exact* json as GET `https://hub.docker.com/search.data?q=disney&page=1&sortby=updated_at&order=asc`
- [ ] 3. The results are properly parsed using the logic learned from [plans/dockerhubsearch.md](plans/dockerhubsearch.md)
- [ ] 4. Search results queries ie "Disney" entered into the search bar populate the `datatable` (with "row" cursor) of results in the Left-Panel area of the screen


### Test Output #01
Hashes are different, responses are different

Source of truth:

```bash
 lsng  curl.exe "https://hub.docker.com/search.data?q=disney&page=1&sortby=updated_at&order=desc" | openssl md5                                                                                                                          
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 15729    0 15729    0     0  64226      0 --:--:-- --:--:-- --:--:-- 64728
MD5(stdin)= 057ce0683dc97d1f1763bc91f31a31d1


Resquest from local is processed by search_dockerhub.py, does not contain pagination markers, is not formtted properly.
 lsng  curl.exe "http://127.0.0.1:8000/search.data?q=disney&page=1&sortby=updated_at&order=desc" | openssl md5                                                                                                                           
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 21340  100 21340    0     0  66273      0 --:--:-- --:--:-- --:--:-- 66479
MD5(stdin)= c12dc49ca8069abbe00b3323f81efce5
```

Console log: `  127.0.0.1:36561 - "GET /search.data?q=disney&page=1&sortby=updated_at&order=desc HTTP/1.1" 200 OK` <-- Receives the request correctly

---


## Fix Plan for Docker Hub Search Sorting Bug

### Root Cause

The bug is in [`search_dockerhub()`](app/modules/search/search_dockerhub.py:78) at lines 109-111:

```python
results, total = get_results(data)
#return format_results_text(results, total, page)
return json.dumps({"results": results, "total": total, "page": page})
```

**Problem**: The function:
1. Correctly passes `sortby` and `order` to Docker Hub (the request is correct)
2. Docker Hub returns properly sorted data in its flat array format
3. BUT then [`get_results(data)`](app/modules/search/search_dockerhub.py:33) extracts and transforms the results
4. Returns a **completely new JSON structure** instead of passing through the original

This is why the MD5 hashes differ - the response is reformatted, losing the original structure including pagination markers.

### The Fix

Per acceptance criteria in [`app/task.md`](app/task.md:64-66), the endpoint must return the **exact same JSON** as Docker Hub. The fix requires:

1. **In [`search_dockerhub()`](app/modules/search/search_dockerhub.py:78)**: Return `response.text` (raw JSON string from Docker Hub) instead of processing it through `get_results()` and reformatting

2. **In [`app/tui/app.py`](app/tui/app.py)**: Update the TUI to parse the raw Docker Hub format using the existing `get_results()` helper function

### Code Changes

**File: [`app/modules/search/search_dockerhub.py`](app/modules/search/search_dockerhub.py)**

Change lines 109-111 from:
```python
results, total = get_results(data)
#return format_results_text(results, total, page)
return json.dumps({"results": results, "total": total, "page": page})
```

To:
```python
# Return raw Docker Hub response as passthrough
return response.text
```

**File: [`app/tui/app.py`](app/tui/app.py)**

The TUI currently expects:
```python
data = response.json()
for r in data["results"]:
    ...
```

It needs to import and use `get_results()` from search_dockerhub to parse the raw Docker Hub format:
```python
from app.modules.search.search_dockerhub import get_results

# In the search worker:
data = response.json()
results, total = get_results(data)
for r in results:
    ...
```

### Verification

After the fix:
- `curl "http://127.0.0.1:8000/search.data?q=disney&page=1&sortby=updated_at&order=desc" | openssl md5` 
- `curl "https://hub.docker.com/search.data?q=disney&page=1&sortby=updated_at&order=desc" | openssl md5`
- Both should produce identical MD5 hashes

Would you like me to switch to Code mode to implement this fix?

---


Now I understand the full picture. Let me create a complete plan that addresses the API passthrough AND keeps the TUI working.

## Complete Fix Plan

### Problem Summary
1. The API must return **exact** Docker Hub JSON (passthrough)
2. The TUI currently expects `{"results": [...], "total": N, "page": N}` 
3. Docker Hub returns a **flat array format** that requires parsing with [`resolve()`](app/modules/search/search_dockerhub.py:12) and [`get_results()`](app/modules/search/search_dockerhub.py:33)

### Solution Architecture

```
Docker Hub API                     Local API (/search.data)              TUI (app.py)
     |                                    |                                  |
     |--- raw flat array JSON ----------->|--- passthrough raw JSON -------->|
                                                                              |
                                                                    import get_results()
                                                                              |
                                                                    parse to get results, 
                                                                    total, page
                                                                              |
                                                                    populate DataTable
```

### Detailed Changes

**1. [`app/modules/search/search_dockerhub.py`](app/modules/search/search_dockerhub.py)**

- Change [`search_dockerhub()`](app/modules/search/search_dockerhub.py:78) to return `response.text` (raw passthrough)
- Add new helper function `get_pagination(data)` to extract page/pageSize from raw format

```python
def get_pagination(data):
    """Extract pagination info from flat array structure."""
    page = 1
    page_size = 30
    for i, v in enumerate(data):
        if v == "page":
            page = resolve(data, data[i + 1]) or 1
        elif v == "pageSize":
            page_size = resolve(data, data[i + 1]) or 30
    return {"page": page, "page_size": page_size}
```

**2. [`app/tui/app.py`](app/tui/app.py)**

- Import the parsing functions from search_dockerhub
- Update [`fetch_page()`](app/tui/app.py:91) to parse raw Docker Hub format

```python
from app.modules.search.search_dockerhub import get_results, get_pagination

# In fetch_page():
data = response.json()  # This is now the raw flat array
results, total = get_results(data)
pagination = get_pagination(data)

self.current_page = pagination["page"]
self.total_results = total

for r in results:
    table.add_row(...)
```

**3. No changes to [`app/modules/api/api.py`](app/modules/api/api.py)** - it just calls `search_dockerhub()` and returns the result

### Verification

After fix:
```bash
# These should produce identical MD5 hashes:
curl "http://127.0.0.1:8000/search.data?q=disney&page=1&sortby=updated_at&order=desc" | openssl md5
curl "https://hub.docker.com/search.data?q=disney&page=1&sortby=updated_at&order=desc" | openssl md5

# Sorting should work - different order = different first result:
curl "http://127.0.0.1:8000/search.data?q=disney&sortby=updated_at&order=asc" | head -c 500
curl "http://127.0.0.1:8000/search.data?q=disney&sortby=updated_at&order=desc" | head -c 500
```

### Summary of Files to Modify

| File | Changes |
|------|---------|
| [`search_dockerhub.py`](app/modules/search/search_dockerhub.py) | Return raw response; add `get_pagination()` helper |
| [`app/tui/app.py`](app/tui/app.py) | Import parsing functions; update `fetch_page()` to use them |

Does this plan look correct? Should I switch to Code mode to implement it?