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
| 22 | query | "disney" | Search query string |
| 24 | searchResults | object | Contains total, results, search_after |
| 26 | total | 203 | Total result count |
| 28 | results | [29,74,91,...] | Array of indices pointing to result objects |
| 555 | search_after | [556,538] | Cursor for pagination |

Per-Result Fields (using first result at index 29)
| Key Index | Key Name | Value Index | Example Value | Web UI Field |
|-----------|----------|-------------|---------------|--------------|
| 30 | id | 31 | "ebusinessdocker/disney" | Repository name |
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

### Validation Against README Examples
From README, result #1 sorted by updated_at desc should be:

aciliadevops/disney-local-node - 1.1K pulls, 0 stars, updated 4 days ago
Checking search-result.json (unsorted, default order):

Index 461: "aciliadevops/disney-local-node" at index 977
pull_count: "1.1K" at index 981
updated_at: "2025-12-29T09:11:32.441859Z" at index 980
Match confirmed.

---
