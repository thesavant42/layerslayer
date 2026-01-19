# Module: sqlite log search + fs viewer for layer peek output

I want to extend the API to add routes that expose the fs-log-sqlite.py script.
- This is very much like peek-all, [docs\api\fastapi-peek-all.md](docs\api\fastapi-peek-all.md)
- This implementation will be minimalist, like with `peek-all`:
    - Import the python script, pass arguments from the API to the fs-log-sqlite.py functions, print the output back out to the browser.



### Task 1 /fslog route
- [ ] Task 1: Extend [app\modules\api\api.py](app\modules\api\api.py) and related files to add a route for `http://localhost:8000/fslog?`
    - [ ] Expose required positional arguments:
          - `image_ref`             # Image reference: `owner/repository:tag`
          - `path`                  # Directory path to list (e.g., "/" or "/etc")  
          - `helpe=true` # display help message (same as --help) when throwing an error or called without arguments, 
          - `layer=0`           # limits output to just layer 0

---

### Task 2 /fslog-search route

- [ ] Task 2 Add a route for `/fslog-search?q=`
    - Extends [docs\api\SEARCH.md](docs\api\SEARCH.md) - Search via fs-log-sqlite.py
- **Works as is today when invoked as a standalone script**

- Import `fs-log-sqlite.py`, pass parameters to the search function and print the output.
    - Very similar to how we imported `main.py` to get the functions for the `peek-all` FastAPI. see: [docs\api\fastapi-peek-all.md](docs\api\fastapi-peek-all.md)
- Should behave like running `python app\modules\fs-log-sqlite.py --search  PATTERN`

---

### Background Information

Here is some example usage and help info for context.

[app\modules\fs-log-sqlite.py](app\modules\fs-log-sqlite.py)

- Displays output from `layer-peek` stored in sqlite, and reconstructing a simulated filesystem.
- Help Message & Command arguments

```bash
usage: fs-log-sqlite.py [-h] [--search PATTERN] [--single-layer] [image_ref] [layer_or_path] [path]

Virtual filesystem navigator for Docker layer logs stored in sqlite

positional arguments:
  image_ref             Image reference: owner/repository:tag
  layer_or_path         Layer index number or path
  path                  Directory path to list (e.g., "/" or "/etc")

options:
  -h, --help            show this help message and exit
  --search, -s PATTERN  Search for files/directories matching pattern (supports SQL LIKE patterns)
  --single-layer        Show single layer instead of merged view (requires layer_index)

Examples:
  fs-log-sqlite.py alpine/git:v2.52.0 "/"
  fs-log-sqlite.py alpine/git:v2.52.0 "/etc"
  fs-log-sqlite.py alpine/git:v2.52.0 0 "/" --single-layer
  fs-log-sqlite.py --search shadow                        # search the database for "shadow"
  fs-log-sqlite.py --search shadow alpine/git:v2.52.0     # search all layers of container image
  fs-log-sqlite.py --search shadow alpine/git:v2.52.0 0   # search single layer of container image

### More Information 

- [docs\api\fslog-API-examples.md](docs\api\fslog-API-examples.md)
- [docs\api\SEARCH.md](docs\api\SEARCH.md) - Search via fs-log-sqlite.py
- Works as is today when invoked as a standalone script
- shares the sqlite database


