# fetcher.py refactor plan

Problem Statement: fetcher.py is over 700 lines of python
- Well above the "100 loc best practice" that is generally taught
- I have copied these functions to new files, but they need to be wired up to their new homes.

Task: 
 - For the functions below
     - 1. Confirm that they have been copied to the file listed in the description of the function in the notes below
         - If they have NOT been copied over, stop editing, make note of where you are in your progress, and alert me at once.
    - 2. After confirming that they have been copied, they need to have all references to them updated to point to their new location.
    - 3. After they've been wired, pause for the user to verify by testing that the application still works.
    - 4. After user confirms, ask the user to delete the old function from fetcher.py
        - 5. pause until the user confirms, then proceed to the next subtask.

## Acceptance Criteria:

- `python layerslayer.py -t ubuntu:24.04 --carve-file /etc/passwd` is able to download a fresh copy of the passwd file.


## Copied Functions, ready to wire

These functions have been copied out of fetcher.py (and a couple from utils.py) and now need to have all references updated to their new locations.

They likewise have not been deleted from fetcher.py (or utils.py, respectively)

#### Begin functionns to wire

- Data Classes for Streaming Peek Results, `fetcher.py` line 28-81 (53 lines)
    -  copied into app\modules\keepers\layerSlayerResults.py, need to update references to point to new file

- `class LayerPeekResult`
- `class LayerSlayerResult`

- fetcher.py lines 82 - 114 (32 lines) COPIED to app\modules\auth\auth.py, NEED TO UPDATE FILES REFERENCING THEM

- `def fetch_pull_token copied to app\modules\auth\auth.py`
    - need to update files that referenced this function in `fetcher.py`
-# 115 - 178 (63 lines)
    - COPIED, NEED TO UPDATE FILES REFERENCING THEM

- Manifest & Config Fetching
    - `def get_manifest`
        - copied to `app\modules\keepers\downloaders.py`
    - `def fetch_build_steps`
            - `app\modules\keepers\downloaders.py`
        - need to udpate references, no longer point to `fetcher.py`
    
- 179 - 215 (36 lines)
    - Layer Download (Full) <--- COPIED, NEED TO UPDATE FILES REFERENCING THEM

- `def download_layer_blob` copied to `app\modules\keepers\downloaders.py`
    - need to update references to this function instead of `fetcher.py`

## Peekers

- fetcher.py 216 - 650 (434 lines)
    # Layer Peek - Streaming with complete enumeration 
    - COPIED, NEED TO UPDATE FILES REFERENCING THEM

- `def peek_layer_blob` copied to `app\modules\finders\peekers.py`
    - need to update all files that referenced fetcher.py for this functuion
- `def peek_layer_blob_complete` copied to `app\modules\finders\peekers.py`
    - need to update all files that referenced fetcher.py for this functuion
- `def peek_layer_blob_streaming` copied to `app\modules\finders\peekers.py`
    - need to update all files that referenced fetcher.py for this functuion

# 651 -737 (86 lines) -
# Layer Slayer: Bulk Layer Peek
`def layerslayer` - copied to `app\modules\keepers\layerSlayerResults.py`, need to update files to point to new location.

### Formatters <--- COPIED, NEED TO UPDATE FILES REFERENCING THEM
- `def _tarinfo_mode_to_string` copied to `app\modules\formatters\formatters.py`
    - need to find and update files that reference these functions from `fetcher.py`
- `def _format_mtime` copied to `app\modules\formatters\formatters.py`
    - need to find and update files that reference these functions from `fetcher.py`

---

### Function to remoe without copying:

** FLAG FOR REMOVAL **
    fetcher.py - `def peek_layer_blob_partial` <-- TODO REMOVE! 
