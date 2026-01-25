
### Current:

This table represents the Results Widget of the TUI app:


```
+-------------------------------+-------------------------------+
| [        search   bar                                      ]  |
+-------------------------------+-------------------------------+
|          Repo List            |       [  TAGS    SELECT    ]  |
|-------------------------------|-------------------------------|
| SLUG | FAV | PULLS | UPDATED  | architecture: amd64           |
| ...  | ... |  ...  |  ...     | os: linux                     |
| ...  (scrollable rows)  ...   | ...                           |
|                               | rootfs.type: layers           |
+-------------------------------+ rootfs.diff_ids[0..6]: sha256 |
|       (empty / dead space)    |                               |
+-------------------------------+-------------------------------+
```
- The "Search input is part of the Top-Panel
- There's a large panel of unused display area beneath the rows

![Current Layout](/plans/current.png)

### Proposed:

This table demonstrates the table after the move:
```
+-------------------------------+-------------------------------+
|																|
+-------------------------------+-------------------------------+
| [ search bar                ] |      [  TAGS   SELECT        ]|
|-------------------------------|-------------------------------|
| SLUG | FAV | PULLS | UPDATED  | architecture: amd64           |
| ...  | ... |  ...  |  ...     | os: linux                     |
| ...  (scrollable rows)  ...   | ...                           |
| ...  (more visible rows) ...  | rootfs.type: layers           |
| ...  (no dead space)      ... | rootfs.diff_ids[0..6]: sha256 |
+-------------------------------+-------------------------------+
```
- "Search Dockerhub" Input widget moves: 
	- from `TopPanel` 
	- to the Results Widget Area,
	- Paralell with "Tags" select Widget in `Right Panel`.
- `TopPanel` is Now Empty
- No Dead space 


This graphic represents to proposed redesign:

![Proposed Layout](/plans/resuts-movedjpg.jpg)

