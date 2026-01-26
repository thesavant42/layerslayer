# User Story : simulated file system, aka layer peeking

## Story so far
I want to find a specific file among a collection of docker hub containers.

I search using the search widget, I click the results of the repo I want to enumerate and the tags are populated. When I use the Select widget I choose a tag, and the imaage config build manifest is displayed, and ends in a list of sha256 digests, one for each layer.

## New Story component: peeking layers and viewing the fslog of the results.
(using drichnerdisnet/ollama:v1 as example.
)
- 1. When I scroll and see the digest of layers available, I select one of them and hit enter. 
    - which kicks off the following sequence:
        - Check to see if layer has already been peeked by issing a status check to the API:
            `http://localhost:8000/peek?image=drichnerdisney%2Follama%3Av1&layer=36&arch=0&hide_build=false&status_only=true`
            - If it has been peeked already the layer status will indicate true for any layer that has already been peeked:

```json
{
  "image": "drichnerdisney/ollama:v1",
  "config_digest": "sha256:ca8d937e089ff0c435b1166a42e7661bb02feb67e31a2eea952751da1c175c33",
  "config_cached": true,
  "layer_count": 37,
  "layers": [
    {
      "idx": 0,
      "digest": "sha256:5a7813e071bfadf18aaa6ca8318be4824a9b6297b3240f2cc84c1db6f4113040",
      "size": 29754290,
      "peeked": true,
      "peeked_at": "2026-01-23T17:06:57.513895",
      "entries_count": 0
[]...truncated for demonstrating to the AI the otput]
  ],
  "peeked_count": 37,
  "unpeeked_count": 0
}
```
 - **Key insight**: Layers are peeked individually
     - The same file can exist in multiple layers
     - We want to investigate all versions, so do not make any assunptions about what to keep
- **Key Insight** Only layers that have been peeked can be Viewed
    - If it has NOT been peeked, it must first be peeked, and can then be viewed.
    - Only the requested layer may be peeked.


- 2. If the layer has *not been cached*, **it must be "peeked"**: (Example request for layer idx[36])
`http://localhost:8000/peek?image=drichnerdisney%2Follama%3Av1&layer=36&arch=0&hide_build=false&status_only=false`

![example of output of peek layer 36](/plans/peek-output.png)

This process does not need to be visible to the end user; It can happen in the background as the user is directed to the "FileSystem Simulation" Tab.

## Viewing Layer Filesystems

/fslog displays the output of the sqlite database's peek layer contents. 

`http://localhost:8000/fslog?image=drichnerdisney%2Follama%3Av1&path=%2F&layer=0` 
### Example layer 0 output
```bash
lrwxrwxrwx       0.0 B  2024-04-22 06:08  bin -> usr/bin
drwxr-xr-x       0.0 B  2024-04-22 06:08  boot/
drwxr-xr-x       0.0 B  2025-01-26 18:09  dev/
drwxr-xr-x       0.0 B  2025-01-26 18:09  etc/
drwxr-xr-x       0.0 B  2025-01-26 18:09  home/
lrwxrwxrwx       0.0 B  2024-04-22 06:08  lib -> usr/lib
lrwxrwxrwx       0.0 B  2024-04-22 06:08  lib64 -> usr/lib64
drwxr-xr-x       0.0 B  2025-01-26 18:03  media/
drwxr-xr-x       0.0 B  2025-01-26 18:03  mnt/
drwxr-xr-x       0.0 B  2025-01-26 18:03  opt/
[]...]
```

This is a backstop file system display that utilizes the correct tables in the sqlite database, but does not return structured data, it's not yet a widget.

The fsslog-sqlite file has patterns that can be learned from and copied into a proper filesystem simulation widget dataTable with a row cursor.

### Navigation

By altering the {path} argumwent of fslog I can change the folder of the output. 
`http://localhost:8000/fslog?image=drichnerdisney/ollama:v1&path=/etc&layer=0`

#### Example: /etc

```bash
-rw-------       0.0 B  2025-01-26 18:03  .pwd.lock
drwxr-xr-x       0.0 B  2025-01-26 18:09  alternatives/
drwxr-xr-x       0.0 B  2025-01-26 18:03  apt/
-rw-r--r--      2.3 KB  2024-03-31 01:41  bash.bashrc
-rw-r--r--     367.0 B  2022-08-02 08:34  bindresvport.blacklist
drwxr-xr-x       0.0 B  2025-01-26 18:09  cloud/
drwxr-xr-x       0.0 B  2025-01-26 18:09  cron.d/
drwxr-xr-x       0.0 B  2025-01-26 18:09  cron.daily/
[...]
```

### Viewing All Layers at once

- By **not** providing a layer idx value, all layers will be displayed in a unified output.
    - `http://localhost:8000/fslog?image=drichnerdisney/ollama:v1&path=/`
    - A file that is superceded by a later layer is marked as `overridden`, but is still addressable. 
    - Symbolic links are indicated as such and can be followed to their intended destination.

### Example of overridden output

```bash
drwxr-xr-x       0.0 B  2025-10-08 22:11  etc/                                               [L15] (overridden)
drwxr-xr-x       0.0 B  2025-10-08 22:07  etc/                                               [L14] (overridden)
drwxr-xr-x       0.0 B  2025-10-08 22:07  etc/                                               [L13] (overridden)
```

## Key Insight:
- Multiple layers can be viewed at once
- The fslog-sqlite.py file is a backstop that produces plain text output
    - If raw json is needed, this will require SLIGHT refactoring to use the json unformatted.
- End user does not need to see the results of the peek process
    - Should still be present in the console logs



## Where to print this output?
Where will fslog output be displayed?

- New tab for tabbedcontent on `LeftPanel` - "FS Simulator"
    - dataTable with row cursor, zebra mode, etc.
    - Need to add in '..' directory breadcrumbs to navigate "back" a directory.

- [ ] Task: Add New Tab to LeftPanel with a /fslog dataTable Widget
- [ ] When I click enter on a sha256:digest from an Image Config manifest in the RightPanel, it should trigger a pre-flight check and and peek if necessary, then populate the widget