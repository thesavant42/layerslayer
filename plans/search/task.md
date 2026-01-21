# Docker Hub Search Module


As a researcher I want to be ablel to quickly find users, orgs, containers, and other docker hub assets quickly using the API.

Would like to search for a term, parse the results, support pagination and sorting.

paginated example, updated_at, order=desc: `&page=2&sort=updated_at&order=desc`
pull_count example: `&sort=pull_count&order=desc`


```bash
 python .\plans\search\search-dockerhub.py -q yahoo

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
rajshekharshankarghodageri/yahoo         0    20     09-01-2023   09-01-20231
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



- [ ] Task Enable - API Route
 `http://localhost:8000/search.data?q=query&page=1&sort=updated_at&order=desc` [API route](app\modules\api\api.py)
    - support pagination
    - support `sort` and `order by`
    - pass through to the remote API, do not try to format it (https://hub.docker.com/search.data)
    - Import [main.py](main.py), argvars -> api.php to parse variables

