- layerslayer.py - TODO: audit for refactoring into submodules
lines 100-340 - these seem like they're the "main" app, can they be made into main.py officially?

- Then I want to move layerslayer.py's remaining functionality to app\modules\keepers\




## Carve Mode Todo 
- I need to fix two issues with Carve mode:
    - 1. The file always saves to `carved/` by default, refactoring into `app\loot` as the default directory
    - 2. THe file name is preserved as-is, which clobbers the previous file search if the file name is the same.
        - need to add `hostname-file-dd-mm-yyyy-HMS-` to the file name to ensure uniqueness
            - My preference is to create a new subdirectory for each carve mode "run" and preserve the file paths within that folder
 
```bash 
(base) \clean-cache.ps1;  python layerslayer.py -t ubuntu:24.04 --carve-file /etc/shadow
 Welcome to Layerslayer 

[*] Carve mode: extracting /etc/shadow from ubuntu:24.04

Fetching manifest for library/ubuntu:24.04...
Found 1 layer(s). Searching for /etc/shadow...

Scanning layer 1/1: sha256:20043066d3d5c...
  Layer size: 29,724,688 bytes
  Downloaded: 65,536B -> Decompressed: 300,732B -> Entries: 143
  FOUND: /etc/shadow (502 bytes) at entry #143

Done! File saved to: carved\etc\shadow
Stats: Downloaded 65,536 bytes of 29,724,688 byte layer (0.2%) in 1.08s
```


### Future Tasks:
- Refactor `app\modules\registry-raider.py` into modules that work with layerslayer
    - Does not attempt any authentication, only works on registries with zero authentication
    - 
### Migrate ls
