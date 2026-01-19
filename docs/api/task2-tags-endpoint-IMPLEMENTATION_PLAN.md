# Implementation Plan: FastAPI Docker Hub Tags Proxy Endpoint
**COMPLETE! IMPLEMENTED!**
## Overview

Extend the existing FastAPI application to add a new endpoint that proxies Docker Hub's repository **Tags listing API**.

The lsng `/repositories` endpoint currently accepts `namespace` as a parameter, signifying a repository's owner.

The DockerHub API *to be proxied* is invoked like this in prod:
    - `https://hub.docker.com/v2/repositories/aciliadevops/memcached/tags?page=1&page_size=10&ordering=last_updated`, 
- Response from the LSNG API must correlate to this link in the upstream API:
    - `http://localhost:8000/repositories/aciliadevops/memcached/tags?page=1&page_size=10&ordering=last_updated`,

Requirements
- 1. Need to add extend the current `/repositories` (pass through) to support `reoponame`/tags 
    - **Note: This is pass through**, so the json response should be *identical* to the upstream API server. 
---

## Acceptance Criteria

- [ ] Should pass through the request from the API to the upstream API and return the response unaltered.
    - `https://hub.docker.com/v2/repositories/library/ubuntu/tags?page=1&page_size=10&ordering=last_updated` <-- Upstream API 
    - `https://localhost:8000/repositories/library/ubuntu/tags?page=1&page_size=10&ordering=last_updated` <-- should return the *identical* json as
- [ ] Pagination must still work as expected.
    - `https://localhost:8000/repositories/library/ubuntu/tags?page=1&page_size=1&ordering=last_updated` (page_size = 1) should return the same result as
    - `https://hub.docker.com/v2/repositories/library/ubuntu/tags?page=1&page_size=1&ordering=last_updated` (page_size = 1)
- Minimalist to pass through the requests. Must adhere to KISS model for simplicity.


### Example Endpoint

```
GET /repositories/{namespace}/{repo}/tags?page={NaN}&page_size={NaN}&ordering={ordering-criteria} # `ordering-criteria` should default to `last_updated`
```
 

## Expected Output Format

The response must be an exact JSON passthrough from Docker Hub.
