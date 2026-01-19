# Research making a --peek-all FastAPI

## Description:

A new bare-minium RESTful FastAPI: `/peek-all?image=owner/repo:tag&arch=0`
Where:
- the endpoint would be `/peek-all?`
    - `image` = the reference <namespace>/<repository>:<tag>
    - `arch=0` = Architecture dict `index[0]`
    - `--force` (optional)
- Route should be equivalent action to running `python main.py -t "moby/buildkit:latest" --peek-all` 

- [x] Task 1. Research the [main.py](main.py) and trace interactive mode to understand what needs to happen to enable fully unattended --peek-all command execution.

- [x] Task 2. Research the [main.py](main.py) and need to add a --force option to allow a fully unttended code execution, without requiring the user to interact once the script has begun.

- [ ] Task 3. Implement a fastAPI route `/peek-all?image=owner/repo:tag&arch=0` to enable the workflow described in the user story.