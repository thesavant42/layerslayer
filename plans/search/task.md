# Docker Hub Search Module


As a researcher I want to be ablel to quickly find users, orgs, containers, and other docker hub assets quickly using the API.

Appears to be JSON from a Svelte app

[plans\search\dockerhubsearch.md](plans\search\dockerhubsearch.md)

[plans\search\search.data](plans\search\search.data)


Would like to search for a term, parse the results, support pagination and sorting.

`&page=2&sort=updated_at&order=desc`
`&sort=pull_count&order=desc`

Deliverable: 

a python scrupt search.py that takes arguments:
- q = query"
- page = NaN
- sort = pull_count, updated_at
- order (ascen, desc)