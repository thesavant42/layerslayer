# Implementation Plan: FastAPI Docker Hub Repository Proxy
Pass through proxy route for Docker Hub's "/v2/repositories" API endpoint
## Overview

As as investigator I want to use lsng to investigate repositories on Docker Hub belonging to user "aciliadevops". To achieve this I will access the `/repositories` route and provide thesavant42 as the `namespace` parameter. 
Example:
`http://localhost:8000/repositories?namespace=aciliadevops` requests `https://hub.docker.com/v2/repositories/aciliadevops` and returns JSON for that namespace:

```json
{
    "count": 98,
    "next": null,
    "previous": null,
    "results": [
        {
            "affiliation": "",
            "categories": [],
            "content_types": [
                "image"
            ],
            "date_registered": "2020-01-06T16:39:19.238146Z",
            "description": "Memcached image",
            "is_private": false,
            "last_modified": "2024-10-16T13:48:34.145251Z",
            "last_updated": "2020-05-04T13:04:44.656071Z",
            "media_types": [
                "application/vnd.docker.container.image.v1+json"
            ],
            "name": "memcached",
            "namespace": "aciliadevops",
            "pull_count": 170,
            "repository_type": "image",
[...continues...]
```

There are **98** repositories for that namespace, which will require pagination to retrieve all results.

## PAGINATION

- By default, if there are more than 10 results for a namespace, the response will be split amongst multiple pages.  The JSON body will contain a link to the next page of results:

```json
"count": 98,
    "next": "https://hub.docker.com/v2/repositories/aciliadevops?page=2&page_size=10",
    "previous": null
    "results": [
    [...contines...]
```

- We must expose the pagination elements `page=NaN&page_size=NaN` to the route

### Pagination Handling

```
while next_url is not None:
    fetch(next_url)
    append results to accumulated list
    next_url = response["next"]
```

## Task

### Task: New Fast API route: `/repositories?namespace=`
Extend the FastAPI routes, add `/repositories`, that will proxy Docker Hub's `repository` listing API.
- 1. The route should add an endpoint that 
    - 1. accepts a `namespace` query parameter (required),
    - 2. accepts `page` and `page_size` as (optional) parameters for pagination
- 2. fetches all results from Docker Hub, 
- 3. and returns an aggregated JSON response matching the exact format of the provided [test fixture](repositories-aciliadevops.json).

### Validation

- The route for `/repositories?namespace=aciliadevops` must return the same JSON as `https://hub.docker.com/v2/repositories/aciliadevops` [must match json here](repositories-aciliadevops.json)
- The route for `/repositories?namespace=aciliadevops&page=1&page_size=1` must return the same JSON as `https://hub.docker.com/v2/repositories/aciliadevops?page=1&page_size=1` [must be a 1:1 match with repositories-aciliadevops-size-1.json](repositories-aciliadevops-size-1.json) 
- The route for `/repositories?namespace=aciliadevops&page=1&page_size=100` must return the same JSON as `https://hub.docker.com/v2/repositories/aciliadevops?page=1&page_size=100` [must be a 1:1 match with repositories-aciliadevops-size-1.json](repositories-aciliadevops-size-100.json)

## Acceptance Criteria

 MUST USE MINIMALIST LOGIC
 - Must follow the KISS model for simplicity
 **JSON must be precisely the same, do not try to reconstruct the JSON. Pass it through as-is only.**


## Dependencies (already installed)

From `requirements.txt`:
- `fastapi` — Web framework
- `uvicorn` — ASGI server
- `pydantic` — Data validation
- `httpx` — Async HTTP client
- `python-dotenv` — Environment variables


