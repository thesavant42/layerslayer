# Docker Hub Search Module

## User Journey
As a researcher I want to be ablel to quickly find users, orgs, containers, and other docker hub assets quickly using the API.
Would like to search for a term, parse the results, support pagination and sorting.

### Example of a paginateted result with sort and order
- paginated example, updated_at, order=desc: 
    - `&page=2&sort=updated_at&order=desc`
- pull_count example: 
    - `&sort=pull_count&order=desc`

### Works as a standalone as of now:

- The search script is currently ready to be wired up to the API, and works as a standalone script:

```bash
 python .\app\modules\search\search-dockerhub.py -q yahoo

Total: 568 results

SLUG                                     FAV  PULLS  CREATED      UPDATED      DESCRIPTION
----------------------------------------------------------------------------------------------------
shalder88/yahoo                          1    1.8K   03-08-2018   03-12-2018   Test Yahoo
rhiaqey/yahoo                            0    7.5K   02-15-2024   01-10-2026
manojkrishnappa/yahoo                    2    383    04-05-2023   04-05-2023
manoj14061996/yahoo                      0    119    11-24-2022   11-24-2022
bravo90503/yahoo                         0    110    05-14-2021   09-06-2023
naboo52/yahoo                            0    87     02-28-2018   02-28-2018
pantone278/yahoo                         0    60     11-14-2023   12-10-2023
mungu42/yahoo                            0    53     04-19-2020   04-19-2020
russwell/yahoo                           0    47     01-07-2024   03-28-2024
manjukolkar007/yahoo                     0    43     01-09-2025   01-09-2025
eimteyaz/yahoo                           0    40     12-04-2018   12-04-2018
anyangpeng/yahoo                         0    35     09-28-2022   09-28-2022
raju991655/yahoo                         0    30     08-24-2024   08-25-2024
doms1997/yahoo                           0    26     10-17-2022   10-17-2022
rajshekharshankarghodageri/yahoo         0    20     09-01-2023   09-01-2023
rrjj/yahoo                               0    20     07-17-2024   07-17-2024
shaikhsohail/yahoo                       0    19     06-03-2022   06-06-2022
mounika2230/yahoo                        0    16     07-31-2023   07-31-2023
gbhandari/yahoo                          0    15     10-02-2021   10-02-2021
binduhp/yahoo                            0    14     07-08-2023   07-08-2023
sanjayhoysal/yahoo                       0    14     11-23-2023   11-23-2023
kvr6060/yahoo                            0    14     07-22-2022   07-22-2022
bala3008/yahoo                           0    14     11-23-2023   11-23-2023
airbyte/source-yahoo-finance-price       0    8.1K   08-22-2023   05-24-2025
shreedevib/yahoo                         0    13     03-02-2023   03-02-2023
ramakrishna1206/yahoo                    0    11     07-31-2023   07-31-2023
athenz/athenz                            5    100K+  04-18-2017   10-07-2017   https://github.com/yahoo/athenz
bsimhaks/yahoo                           0    10     05-31-2023   05-31-2023
mohancm98/yahoo                          0    7      06-06-2023   06-06-2023
sony923/yahoo                            0    5      09-13-2023   09-13-2023
```

Pagintion and sorting are functional. Here's the sample Help output:

```bash
C:\Users\jbras\GitHub\lsng>python .\app\modules\search\search-dockerhub.py --help
usage: search-dockerhub.py [-h] [-q QUERY] [--page PAGE] [--sort {pull_count,updated_at}] [--order {asc,desc}]
                           [--file FILE]

Search Docker Hub

options:
  -h, --help            show this help message and exit
  -q, --query QUERY     Search query
  --page PAGE           Page number
  --sort {pull_count,updated_at}
                        Sort field
  --order {asc,desc}    Sort order
  --file FILE           Load from local JSON file (for testing)
```


## Tasks

- [x] Migrate search script to app module search folder
    - done! `app\modules\search\search-dockerhub.py`
- [ ] Wire up  `app\modules\search\__init__.py`
- [ ] Task Enable - API Route
    - `http://localhost:8000/search.data?q=query&page=1&sort=updated_at&order=desc`
        -  [API route](app\modules\api\api.py)
    - Must support pagination passthrough
    - Must support `sort` and `order by` passthrough
    - Passthrough to up stream API
    - Import [main.py](main.py), argvars -> [api.py](app\modules\api\api.py) to parse variables
      -I think this pattern (for /repositories) makes sense for passthrough and pagination to copy these patterns for `/search.data?`: 
   - [app\modules\api\api.py:93-116](app\modules\api\api.py:93-116)

## Example Pattern from API.py 
```python
    # TODO Use this pattern as a model for Search
    @app.get("/repositories")
    async def repositories(
        namespace: str,
        page: int = Query(default=None),
        page_size: int = Query(default=None)
    ):
        """
        Pass-through proxy for Docker Hub's /v2/repositories API.
        Returns the upstream JSON response verbatim.
        """
        url = f"https://hub.docker.com/v2/repositories/{namespace}"
        params = {}
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return JSONResponse(content=response.json(), status_code=200)
    ```

## Acceptance Criteria

- API route exposed: `/search.data?`
    - `q` for query (query, mandatory field)
    - `page` for page number (optional, default to `1`)
    - `sort` for sorting criteria, (optional, default to `updated_at`, other column identifiers. Default to `updated_at`)
    - `order` for sorting order, (optional, `ascen` or `desc`, defaukt to `desc)