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