# Research making a --peek-all FastAPI

## Description:

A new bare-minium RESTful FastAPI: `/peek-all?image=owner/repo:tag&arch=0`
Where:
- the endpoint would be `/peek-all?`
    - `image` = the reference <namespace>/<repository>:<tag>
    - `arch=0` = Architecture dict `index[0]`
- Route should be equivalent action to running `python main.py -t "moby/buildkit:latest" --peek-all` 

**Critical Insight: Dependancy Unmet: `arch` selection command-line argument.

## Problem Statement 
- Problem Statement: There's currently no way to specify the architecture as a command line argument. As a result, manifests with more than one arch require interactive user intervention, frustrating automation.

### Solution Proposal
- Solution: extend `main.py` to include kwargs for `--arch`, and support selecting from an indexed list.


- [ ] Task 1. Research the [main.py](main.py) and trace interactive mode to understand what needs to happen to enable fully unattended --peek-all command execution.




---

**BLOCKED! Task 1 is a dependancy of adding this API endpoint.

- [ ] Task 2. Implement a fastAPI route `/peek-all?image=owner/repo:tag&arch=0` to enable the workflow described in the user story.