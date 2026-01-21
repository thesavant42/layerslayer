# New Feature - List cached scan results

As a security research I want to avoid sending unnecessary requests to a target system. To aid in this goal, I want to be ablle to query which repositories/images have already been peeked, and are thus able to be used with `fslog`, which requires the full image reference (`namespace/repository:tag`), filesystem path, and layer index integer.

---

## Problem Statement

- But fslog does not work if the image has not already been cached.
- there is no way for a user to know if a layer has already been cached in the database, without sending more packets to the target. 
- But we have the data already in the database

---

## Proposal

- Create a `/history?` [api route](app\modules\api\api.py) enabling a user to view a table of all of the previously-peeked repository images.
- It must support pagination for the results
    - Each page returns 30 results by default (just like Docker Hub),
    -  `page=1`, `page_size=30` modifiers to change the results amount displayed
    - orderby any of the available columns (`scrapedat`, `repo`, `owner`, `tag`, etc) 
- support search of the rows, filter results to only those results with a match.
    - Example: `/history?q=nginx` only shows results that have nginx in the owner name, repo name, or tag.
---

### Resources
s- qlite mcp has connectivity to the sqlite database

### Open Question:

Q: What database elements are best suited for this? We need 
    - the scraped at time,
    - owner,
    - repo  
    - arch 
    - os 
    - layer index number
A: `layer_metadata` table in [lsng.db](app/data/lsng.db) has all of these fields.

Q: Should the output be text or JSON?
A: For the history the results should be printed text, each result is laid out in columns of 1 row.

Q: What fields do you want?
A: **| scrapedat | owner | repo | tag | arch | layerindexnumber | layer_size |**  in that order.
---

## Tasks

- [ ] 1. Create a Fast API route for `/histiory?` 
    - results db: [app/data/lsng.db](app/data/lsng.db)
        -  -> `layer_metadata` table
- With no arguments, print the last `page_size=30` results (default)
    - the owner, repo, tags can all be quite lengthy strings, I added a marker to indicate suggested length limits
        - | scrapedat:12 | owner:<25 | repo:<25 | tag:<20  | arch:<10 | layerindexnumber:<4 | layer_size | 
    - 1 row per result
    - None of the arguments are required, they are optional, and will filter the results

### Acceptance Criteria:
Task is NOT COMPLETED until all criteria are met: 
- [ ] 1. **FastAPI route; `/history?q={query}&page={NaN}&page_size={NaN}&order={asc|desc}&sortby={column}**
- [ ] 2. Prints **FORMATTED TEXT** , NOT JSON!
- [ ] 3. Results can be *sorted*. 
- [ ] 4. Results can be *paginated*.
- [ ] 5. Results can be *filtered*