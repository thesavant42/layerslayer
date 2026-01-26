# Task 3 - Pass through for images
Pass Through route for requesting Images by {TAG}
**COMPLETE! IMPLEMENTED!**
## Overview

Extend the [existing FastAPI application](app\modules\api) to add a new endpoint that proxies Docker Hub's repository **Images listing API**.

Upstream API endpoint to proxy: `https://hub.docker.com/v2/repositories/{NAMESPACE}/{REPO}/tags/{TAG}/images?page_size=NaN&page=NaN&ordering=last_updated`

## Summary

This task is effectively the same as [Task 2](docs\api\task2-tags-endpoint-IMPLEMENTATION_PLAN.md), **except that** this will be using a `{TAG}` to return a list of **oci container images** from the API.


## Acceptance Criteria
- JSON Results from `https://hub.docker.com/v2/repositories/{NAMESPACE}/{REPO}/tags/{TAG}/images?page_size=NaN&page=NaN&ordering=last_updated` must be identical to `http://localhost:8000/repositories/{NAMESPACE}/{REPO}/tags/{TAG}/images?page_size=NaN&page=NaN&ordering=last_updated`
- [ ] Pagination must still work as expected.
    - `https://hub.docker.com/v2/repositories/library/ubuntu/tags?page=1&page_size=1&ordering=last_updated` (page_size = 1) should return the same result as
    - `http://localhost:8000/repositories/library/ubuntu/tags?page=1&page_size=1&ordering=last_updated` (page_size = 1)
- Minimalist to pass through the requests. Must adhere to KISS model for simplicity.


### Example Endpoint

```
GET /repositories/{namespace}/{repo}/tags/{tags}/images?page={NaN}&page_size={NaN}&ordering={ordering-criteria} # `ordering-criteria` should default to `last_updated`
```
 

## Expected Output Format

The response must be an exact JSON passthrough from Docker Hub.
