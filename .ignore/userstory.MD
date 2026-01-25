
### Tags
- `/repositories/{namespace}/{repo}/tags?page=NaN&page_size=NaN&ordering=last_updated`
	- Returns first page of [Tags for a repo](http://localhost:8000/repositories/disneyresolve/vuln-container/tags)
		- 30 results a page,
		- ordered by "last updated" time 
---

## Enumerate

### Image Config
- With the Tags for a repository, I can now construct a full `image_ref`, consisting of `{nameapace}/{repo}:{tag}`
	-	`repositories/disneyresolve/vuln-container:latest`
- With the image_ref  I I can request the **Image build config** [here](http://localhost:8000/repositories/disneyresolve/vuln-container/tags/latest/images?ordering=last_updated), which contains the first trove of metadata, in the form of:
	- Environment Variables
	- Package names
	- Commands used to build the container
	- location within the filesystem where changes occured
	- Comments and build instructions
	- Working Directory, entrypoint, and port exposures
	- **Sha256 Digests of Container Image layers**
	- passwords in command arguments

---	

### Peek (enumerate filesystem layout and permissions)
Once I have the namespace (owner of a repo), the repo, and the tag, I "[peek](/peek)" the image later; enumerate the contents of an image layer, which requires the idx of Image layer to enumerate, or by default will enumerate all layers. I opt for "all" (default) to get the whole image, since it's only a few layers, and the file size indicates the layers are not large.

#### Peek: all layers vs. As needed
- Peek All is more thorough and convenient but takes more time
- 1 layer at a time progressively is more efficient but it becomes possible to skip layers that are not manually reviewed

#### When would I want to peek some vs. peek all?
- In some cases, such as when the container is large and the content of interest is in the 40th layer of 41 layers (which we might have learned by reading the image config) then it does not make sense to enumerate the other layers;

---

## Exfiltrate

### Carve
- After reviewing the contents of the layers' enumerated filesystem, I see a file is added called `/root/secrets.txt` is added during the build instructions on `layer[0]`.
- This file looks like I should investigate it. I could:
	- ~~Be clueless and download the whole container, fire it up, and then login by overriding the entrypoint,~~ NO!
	- Be more clued and download the single layer that has `/root/secrets.txt` and extract the .tar.gz, 
	- **Be yolosint and stream-carve the secrets, never mind the bollocks, using the `/carve` api endpoint.**

 #### I opt to yolosint and use the `/carve` endpoint
- I need the `image`, which is a concatenation of the `{namespace}`/`{repo}`:`{tag}``
- The path to the file, in this case `/root/secrets.txt`
- layer idx is optional, but without it every layer will be searched. layer is idx[0]
- Since the file seems to be plain text I can use the `as_text` option to view the output via stdout instead of saving to file
- After verifying the file is what I want, I make the request again, without applying `as_text`, and the file is streamed to my client and I save the file.


---


## Current Status : Underway
    - https://textual.textualize.io/widgets/select/
        - [ ] select table for tags, drop-down to choose which tag to view image layers for
- [ ] `input` widget for hooking up to `/search.data?` API endpoint

- [ ] Layer Peek debug prints need to be moved to a debug function (from [main.py](main.py) output)
- [x] Need proper progress tracking for layers not-yet-peeked / peek-a-queue

- [ ] Layer Peek UI Flow:
    - 1. Get the Image config(s) for a TAG (Variable architecture, TAGs are per-repository)
    - 2. Review the config(s) from step 1. Build Instructions, meta data, file size, etc... all provide information about which layers are worth "peeking"
    - 3. Peek the layer(s) user has indicated by way of the IDX values, which are present in the config.
    - 4. Display fslog-style output for the peeked layers:
        - 1. one layer at a time by highlighting it, or
        - 2. All layers peeked-so-far by selecting a meta layer
- [ ] Carve Flow from Peek UI
    - 1. After a layer has been peeked, user can review layer contents in `/fslog` view
        - Identify file to peek, by full path and layer `IDX` to pass to carve

 **Design TUI architecture** - the backend is ready, UI is framed, needs to be filled in and wired up.