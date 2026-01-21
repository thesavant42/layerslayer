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

---


- [x] Task 1 - search-dockerhub.py **COMPLETED** [plans\search\search-dockerhub.py](plans\search\search-dockerhub.py)
    - it currently parses the sample search json and prints it out
    - need to wire up searhc: `https://hub.docker.com/search.data?q=disney&order=desc&sortby=updated_at&page=1`

- [ ] Task 2 - API Route
 `http://localhost:8000/search-dockerhub?q=query&page=1&sort=updated_at&order=desc` API route
    - support pagination
    - support `sort` and `order by`