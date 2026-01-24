[container-image-config.json](container-image-config.json)

Below are the line numbers and descriptions corresponding to the container-image-config.json file linked above. The ideal state for a human user consuming this data is to have a formatted text report. For the scope of this project, which is based heavily in OSINT and Metadata collection, this information is highly valuable. 

Each of the areas listed below represent a logical division of the data into unque tables or text labels and their contents.


 - A UI consuming the image config JSON would be concerned with the following fields:


- Line 2: ARCH `."architecture"`
- Line 3: Config Hostname, Domainname, User, Exposed Ports, CMD, Image, Entrypoint, Labels, shELL - `."config" `


- Line 97-101 Container ID Hostname, Domainname, Username (if present)

- Line 105-106 Exposed Port `."config" | ."ExposedPorts"`
    - Super Important
Line 111-167, ENV variables `."config" | ."Env"`
    - Super important

Line 168-175 cmd: array `."config" | ."Cmd"`
    - Extremely important!

Line 178 - Workingdir (if present)
    - Important
    - keep this
Line  179-181 Entrypoint `. | ."config"."Entrypoint"`
    - ABSOLUTELY MUST HAVE THIS
    - Print it in an emphasized typography, bold or in bright colors
    - 
- 183-187 Labels array: `."config" | ."Labels"`
    - important details,
    - we want to keep these 

Line 189-196 Shell[] Shell commands, want to print these in a table

Line 197: `docker_version`: Always good to know


### Build Commands
Line 198 - 846 history  - ` ."history".[]."created_by"`
- This is the GOOD stuff! I want these details
- Table with columns for
    - `created`:    time stamp
    - `created_by`: the command that produced the layer
    - `comment`: often the buildkit version, other comments
    - `empty_layer`: BOOL indicating if there's data to scrape or not
        - Even if the row is empty, I still want the metadata, it's still important

### OS ie "linux"
Line 847 - OS details - ` ."os"`
 - I definitely want the OS and variant info. Print "nul" if it's not present


### Layers
Line 848-EOF - RootFS digest Array `jq ."rootfs"."diff_ids"`
- diff_ids - digest of layers to peek
- Print in a table
- Add a Meta row to select "ALL LAYERS"
    - Future work: UI with selector to 
        - Single Layer:
            - choose a layer to peek (only that layer), or 
            - to download (only that layer)
        - Bulk:
            - peek all layers or 
            - download all layers