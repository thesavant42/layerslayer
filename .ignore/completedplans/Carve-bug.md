# Critical Flaw in file carving logic

File carving logic must require an idx integer when carving files.

## Problem Statement: 
- I need to track changes between files of interest in a container.
- If file `/home/example/secret` contains the values "0" on layer [0] and "password" on layer [42] I *must* be able to know of that change, and save both files.
- PROBLEM 2: This scanning can cause the app to download every single layer and scan them in order to find the file, which is the opposite of the intent of this application suite entirely.

If I try to /carve a file with do not provide the layer IDX the API will scan all layers, beginning at 0, and stop at the first copy of the file it finds.


### Desired Behavior:
- `/carve` **requires** index layer idx to save a file, 
    - returns a helpful error message if it's not provided.
- If a layer idx is provided 
    - it will carve the version of the file from the layer index provided only
    - If a user wants multiple versions of the file, they perform the download per each version of the file

- Task: Implement this user story logic

[carver.py](app\modules\keepers\carver.py) line 363 is about where the Main carve function begins

### Summary
- Layer index IDX is mandatory for all carve, not optional as it is currently.
