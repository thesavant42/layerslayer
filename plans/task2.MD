# dataTable

## Problem Statement:

- The Docker Hub Search Results Widget in `Left-Panel` is a Static Widget, not a [dataTabale](/plans/data_table.md) with row style cursor, as instructed.

- The file that handles dockerhub searches is [/app/modules/search/search_dockerhub.py](/app/modules/search/search_dockerhub.py)

- **CRITICAL INSIGHT** search_dockerhub.py is already capable of pagination via API. 
    - **The plain text output is scaffolding.**
    - Function `format_results_text(results, total, page=1) line 53` must be refactored to output json, which it receives from upstream api already
    - `app.py`  needs to be refactored to accept JSON from search_dockerhub.py and populate a datatable
    - Let textual's built in navigation take over, do not get in the way.
- Textual TUI [app/tui/app.py](app/tui/app.py) makes a request to `search.data`, which has its own search module: [search_dockerhub.py](/app/modules/search/search_dockerhub.py)

Boundary-based pagination should trigger the pagination API call


### Task:
- refactor `search_dockerhub.py` to output json or text 
- Create a `dataTable` widget for `Left-Panel`, 
    - witha "row" cursor, populated with json response from `search_dockerhub.py`
    - textual's row cursor navigation should work if we don't get in the way
    - Do **not** bind *any* additional pagination keys, textual will handle it.

### Links: 
- [Swagger doc](/plans/openapi.json) for LSNG API
- [dataTabale](/plans/data_table.md) Textual dataTable documentation
- [search_dockerhub.py](/app/modules/search/search_dockerhub.py) DockerHub Search Module
- [app/tui/app.py](app/tui/app.py) Textual TUI