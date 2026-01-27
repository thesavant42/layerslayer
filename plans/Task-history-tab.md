
# Task: Add history view to UI

## Problem Statement:
Contents of layer scrapes are saved to the database. There's no way to view them via the UI

- There is a version of this history tab that exists today in the [api.py](/app/modules/api/app.py)

`http://localhost:8000/history?page=1&page_size=30&sortby=scraped_at&order=desc`


```bash
scraped_at   | owner                     | repo                      | tag                  | idx  |   layer_size
-------------+---------------------------+---------------------------+----------------------+------+-------------
2026-01-27   | accurascan                | mrz                       | 38.0.0               | 0    |     76097157
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 38   |          349
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 37   |          343
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 36   |           32
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 35   |     70706031
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 34   |          389
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 33   |          177
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 32   |      5642998
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 31   |      2782352
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 30   |         1117
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 29   |          173
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 28   |          137
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 27   |          144
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 26   |          150
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 25   |    122663174
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 24   |       690253
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 23   |      6195415
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 22   |      1686531
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 21   |        18753
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 20   |       456627
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 19   |     69490589
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 18   |    103985075
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 17   |       462232
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 16   |        19876
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 15   |          185
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 14   |      2167193
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 13   |          143
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 12   |         2303
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 11   |    104523546
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 10   |     81815545
```

Adding q={query} allows the user to filter by key word

- `http://localhost:8000/history?q=disney&page=2&page_size=30&sortby=scraped_at&order=desc`

```bash
scraped_at   | owner                     | repo                      | tag                  | idx  |   layer_size
-------------+---------------------------+---------------------------+----------------------+------+-------------
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 8    |     57160920
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 7    |         4902
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 6    |          505
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 5    |         1806
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 4    |         1507
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 3    |     83453220
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 2    |    142815437
2026-01-27   | accurascan                | mrz-disney                | 1.0.0                | 1    |          675
2026-01-27   | disneycodedisney          | my-node-app               | latest               | 5    |          279
2026-01-27   | disneycodedisney          | my-node-app               | latest               | 4    |           93
2026-01-27   | disneycodedisney          | my-node-app               | latest               | 3    |          449
2026-01-27   | disneycodedisney          | my-node-app               | latest               | 2    |      1386797
2026-01-27   | disneycodedisney          | my-node-app               | latest               | 1    |     46521176
2026-01-27   | disneycodedisney          | my-node-app               | latest               | 0    |      3623844
2026-01-26   | ttyeri                    | disney                    | latest               | 2    |      1262122
2026-01-26   | ttyeri                    | disney                    | latest               | 1    |     51935973
2026-01-26   | ttyeri                    | disney                    | latest               | 0    |      3860104
2026-01-26   | disney2002                | tools                     | latest               | 7    |      9411911
2026-01-26   | disney2002                | tools                     | latest               | 8    |      9479875
2026-01-26   | disney2002                | tools                     | latest               | 9    |          150
2026-01-26   | jcrienen                  | disneyland                | latest               | 7    |          133
2026-01-26   | jcrienen                  | disneyland                | latest               | 9    |       340061
2026-01-26   | dlalanza                  | back-disney               | latest               | 11   |       823704
2026-01-26   | dlalanza                  | back-disney               | latest               | 10   |      2969524
2026-01-26   | tanaebousfiha             | disney                    | latest               | 8    |          765
2026-01-26   | tanaebousfiha             | disney                    | latest               | 7    |           92
2026-01-26   | tanaebousfiha             | disney                    | latest               | 9    |     41508243
2026-01-26   | tanaebousfiha             | disney                    | latest               | 10   |          167
2026-01-26   | ttyeri                    | disney                    | latest               | 3    |          445
2026-01-26   | ttyeri                    | disney                    | latest               | 4    |           93
```

- Similar to Image Config datatables for the Layer Images, clicking the layers in the Queue should load that layer's contents into the FS Simulator tab. 
- There should also be a combined-layers view for each project in the history
- This should be rendered in the Right Panel