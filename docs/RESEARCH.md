# peek-all api research making a --peek-all FastAPI
**Complete! IMPLEMENTED**
## Description:

A new bare-minium RESTful FastAPI: `/peek-all?image=owner/repo:tag&arch=0`
Where:
- the endpoint would be `/peek-all?`
    - `image` = the reference <namespace>/<repository>:<tag>
    - `arch=0` = Architecture dict `index[0]`
    - `--force` (optional)
- Route should be equivalent action to running `python main.py -t "moby/buildkit:latest" --peek-all --arch=0 --force` 

- [x] Task 1. Research the [main.py](main.py) and trace interactive mode to understand what needs to happen to enable fully unattended --peek-all command execution.

- [x] Task 2. Research the [main.py](main.py) and need to add a --force option to allow a fully unttended code execution, without requiring the user to interact once the script has begun.

- [ ] Task 3. Implement a fastAPI route `/peek-all?image=owner/repo:tag&arch=0&force=1` to enable the workflow described in the user story.

`/peek-all?image= owner/repo:tag 
`&arch=0` defaults to arch=0 if not provided.
Defaults to overwrite with `&force=1` if not provided.

API takes GET parameters and uses them to launch `python main.py -t "owner/repo:tag" --peek-all --arch=0 --force` 

thats it. Garbage in, garbage out.

---

Future Tasks: Implement quality of life endpoints in FastAPI 
-- **Dependancy: FastAPI implemented per Task 3**

FastAPI - partial implementation: (not implemented here yet)
- `http://192.168.1.82:3000/dockerdorker/reallyfastapi` 
    - This repository implements a FastAPI proxy for the following endpoints:
    - 
- [x] 1. List REPOs by NAMESPACE
	- Pattern: `/v2/repositories/NAMESPACE/?&page_size=100&page=1&ordering=last_updated` # pagination is hard coded, not exposed to the end user; this is to ensure consistent JSON shape; otherwise the reports will break.
- [x] 2. List TAGS by REPO
	- Pattern: `/v2/repositories/**NAMESPACE**/**REPO**/tags?&page_size=100&page=1&ordering=last_updated` # pagination is hard coded, not exposed to the end user; this is to ensure consistent JSON shape; otherwise the reports will break.
- [x] 3. Get IMAGES by `TAG`, and `NAMESPACE/REPO`
	- Pattern: `/v2/repositories/**NAMESPACE**/**REPO**/tags/**TAG**/images?&page_size=100&page=1&ordering=last_updated` # pagination is hard coded, not exposed to the end user; this is to ensure consistent JSON shape; otherwise the reports will break.
- [x] 4. Get Image Manifest digest IDs by TAG 			# Only in DockerHub, does not exist private container registries
	- Pattern: `/layers/**NAMESPACE**/**REPO**/**TAG**/images/**sha256-DIGEST**.data` # pagination is hard coded, not exposed to the end user; this is to ensure consistent JSON shape; otherwise the reports will break.


`app\modules\fs-log-sqlite.py` - prints the formatted results of a later peek, filtered by directory and layer.