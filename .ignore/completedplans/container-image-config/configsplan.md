# Store Image Configs to sqlite

### Q1: Do we cache image configs to SQLite? Validate before read/write?

**Answer: NO - Image configs are NOT cached.**

The [`get_image_config()`](app/modules/finders/config_manifest.py:12) function fetches configs directly from the registry every time. The SQLite database only stores:
- `layer_metadata` - layer digest, index, size, entry counts
- `layer_entries` - filesystem entries from peeked layers

**Gap identified:** Image configs (ENV vars, CMD, history, labels) are fetched on every request. Consider caching them if performance becomes an issue.

### Problem Statement: We are not saving our image config lookups. 
- This is an OSINT investigation tool
- should avoid making unnecessary lookups to upstream services.
    - Does the config already exist? Look in the database. 
        - If so, load that
        - If not, download the fresh config and store it in the database
     
### Solution: 

1. [Store the Image Configs](app\modules\keepers\storage.py) in [sqlite](app\data\lsng.db)
- Add a new sqlite table
     - add image configs by digest
     - also the source of truth for idx <-> sha256 image digest mappings
2. Create a table to track which
    1.  layers have been peeked or not.
    2. update this once the layer has been peeked
3. Export a mapping of IDX to layer digest
4. When navigating layers with `fslog`, users choose from a list of IDX, avoiding out-of-range errors

