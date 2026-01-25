# Docker Hub Search Module


As a researcher I want to be ablel to quickly find users, orgs, containers, and other docker hub assets quickly using the API.

Appears to be JSON from a Svelte app

[plans\search\dockerhubsearch.md](plans\search\dockerhubsearch.md)

[plans\search\search.data](plans\search\search.data)


Would like to search for a term, parse the results, support pagination and sorting.

paginated example, updated_at, order=desc: `&page=2&sort=updated_at&order=desc`
pull_count example: `&sort=pull_count&order=desc`




Deliverable: 

a python script, search-dockerhub.py that takes arguments:
- q = query"
- page = NaN
- sort = pull_count, updated_at
- order (ascen, desc)


... and returns formatted text results of a dockerhub search.

- [ ] Task 1 - search-dockerhub.py
- it should work stand alone first
- once I am happy with the format I will move on to implementing the pattern as an API route.

- [ ] Task 2 - API Route
 `http://localhost:8000/search-dockerhub?q=query&page=1&sort=updated_at&order=desc` API route
    - support pagination
    - support `sort` and `order by`


##### Response Format Overview

The response is a flat JSON array where:

- String values are stored at specific indices
- Objects use {"_N": M} syntax meaning "key at index N has value at index M"
- Negative values like -5 and -7 appear to mean null or undefined
- The results array contains indices pointing to result objects

### Documented Field Mappings

Top-Level Structure
| Index | Key | Value | Notes |
|-------|-----|-------|-------|
| 22 | query | "acme" | Search query string |
| 24 | searchResults | object | Contains total, results, search_after |
| 26 | total | 203 | Total result count |
| 28 | results | [29,74,91,...] | Array of indices pointing to result objects |
| 555 | search_after | [556,538] | Cursor for pagination |

Per-Result Fields (using first result at index 29)
| Key Index | Key Name | Value Index | Example Value | Web UI Field |
|-----------|----------|-------------|---------------|--------------|
| 30 | id | 31 | "ebusinessdocker/acme" | Repository name |
| 32 | name | 31 | same as id | Repository name |
| 33 | slug | 31 | same as id | URL slug |
| 34 | type | 35 | "image" | Result type |
| 36 | publisher | 37 | {id, name} | Publisher/namespace |
| 40 | created_at | 41 | "2017-04-25T09:11:17.568035Z" | Creation date |
| 42 | updated_at | 43 | "2017-11-02T07:47:35.758489Z" | Last Updated |
| 44 | short_description | 45 | "" | Description |
| 46 | badge | 47 | "none" | Badge type |
| 48 | star_count | 49 | 0 | Stars |
| 50 | pull_count | 51 | "270" | Pulls (string!) |
| 52 | logo_url | 53 | {} | Logo URLs |
| 55 | categories | 56 | [] | Categories |
| 57 | operating_systems | 58 | array | OS list |
| 63 | architectures | 64 | array | Architectures |
| 69 | media_types | 70 | array | Media types |
| 72 | content_types | 73 | array | Content types |

Pagination Fields
| Index | Key | Value |
|-------|-----|-------|
| 624 | page | 1 (from index 428) |
| 625 | pageSize | 30 (from index 626) |


---
Fields to print:

| slug | star_count | pull_count | publisher_name | created_at | updated_at | short_description |

- MM-DD-YYYY date format
- You are NOT PERMITTED to truncate!