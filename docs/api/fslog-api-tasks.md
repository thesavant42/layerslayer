# Module: sqlite log search + fs viewer for layer peek output
**COMPLETED**
I want to extend the API to add routes that expose the fs-log-sqlite.py script.
- This is very much like peek-all, [docs\api\fastapi-peek-all.md](docs\api\fastapi-peek-all.md)
- This implementation will be minimalist, like with `peek-all`:
    - Import the python script, pass arguments from the API to the fs-log-sqlite.py functions, print the output back out to the browser.



### Task 1 /fslog route
- [x] Task 1: Extend [app\modules\api\api.py](app\modules\api\api.py) and related files to add a route for `http://localhost:8000/fslog?`
    - [x] Expose required positional arguments:
          - `image_ref`             # Image reference: `owner/repository:tag`
          - `path`                  # Directory path to list (e.g., "/" or "/etc")  
          - `helpe=true` # display help message (same as --help) when throwing an error or called without arguments, 
          - `layer=0`           # limits output to just layer 0

---

### Task 2 /fslog-search route

- [x] Task 2 Add a route for `/fslog-search?q=`
    - Extends [docs\api\SEARCH.md](docs\api\SEARCH.md) - Search via fs-log-sqlite.py
- **Works as is today when invoked as a standalone script**

- Import `fs-log-sqlite.py`, pass parameters to the search function and print the output.
    - Very similar to how we imported `main.py` to get the functions for the `peek-all` FastAPI. see: [docs\api\fastapi-peek-all.md](docs\api\fastapi-peek-all.md)
- Should behave like running `python app\modules\fs-log-sqlite.py --search  PATTERN`

