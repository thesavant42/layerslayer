## USER STORY

I want to find containers related to a topic, "disney" in this example.

## Start
- I open the app and see:
	1. [a table of recently assesed containers](http://localhost:8000/history)
	2. An option to ["search recent"](http://localhost:8000/history?q=disney&page=2) (meaning recetly assessed containers)
		a. Search for key word in namespace, repo, or tag in sqlite
	3. An option to "search Docker Hub"
		- Routes to the `/search.data` [Docker Hub passthrough route](http://localhost:8000/search.data?q=disney)


### search.data
- I search the recents, and, finding 0 matches, opt for #3, `/search.data` [here](http://localhost:8000/search.data?q=disney)
	- Each result is for 1 respository in includes the namespace/owner of the repository.
	- If the namespace, repository name, or description seem worth investigating I will want to dig in on a repository.
	- To view files or folders we need to get the [TAGs](###Tags) available in a repository via the `/repositories/{namespace}/{repo}/tags` API.

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


## Open Questions:


Q: Do we cache the image configs to the sqlite database when we enumerate them?
	- If so, do we validate whether its been cached before reading or writing?
A: \

Q: When carving a layer we accept a layer idx but do not require one, nor do we require a lookup in the database. 
Do we present the user with a warning if 
	1. a carve has been requested, and 
	2. a layer has not been provided, and 
	3. There's no idx for that carve in the database?
A: \

Q: Is there at present a mapping of idx to sha256 digest? When addressing by index there's no way for a user to know if the next layer will be out of range.
---

## Current Status : Not Achieved

- [ ] There is no UI at this point in time.
	- I want to make a Textual TUI and enable the [textual-web](https://github.com/Textualize/textual-web) library.
- [ ] select table for tags, drop-down to choose which tag to view image layers for
- [ ] Layer Peek debug prints need to be moved to a debug function
- [ ] Need proper progress tracking for layers not-yet-peeked / peek-a-queue
- [ ] Layer Peek UI Flow:
	- Option A: JIT layer peeking
		Assuming all containers begin with layer[0]
		/fslog view the path at layer[0]
		- remaining layers[1+] are peeked in the background
		- Alert when all layers have been peeked and are ready
		- Users only need the <image_ref> ({namespace}/{repo}:{tag})
		- Downside: Could be extremely slow
	- Option B: JIT, selective layers
		- Like Option A, but instead of background and viewing all layers, pick the layer to enter from,
			- need a way to +/- navigate each layer
		- Upside: trade off of speed and efficiency
		- Downside: Coupld miss important data
		If I could visually indicate layers that have been peeked or not I could create a workflow around 

--

## User Journey vs API Coverage Summary

### Visual Flow

```mermaid
flowchart TD
    subgraph Discovery[1. Discovery - IMPLEMENTED]
        A[/history - view cached] --> B[/history?q= - search cached]
        B --> C[/search.data - search Docker Hub]
    end

    subgraph Navigation[2. Navigation - IMPLEMENTED]
        D[/repositories/ns/repo/tags - get tags] --> E[/repositories/.../config - image config]
    end

    subgraph Enumeration[3. Enumeration - IMPLEMENTED]
        F[/peek - enumerate filesystem] --> G[/fslog - browse filesystem]
        G --> H[/fslog-search - search files]
    end

    subgraph Extraction[4. Extraction - IMPLEMENTED]
        I[/carve - extract single file] --> J[/layer/download - download layer]
    end

    Discovery --> Navigation --> Enumeration --> Extraction
```

**Result: All 10 API endpoints for the user journey are implemented. The gaps are UI/UX only.**

---

## Answers to Open Questions

### Q1: Do we cache image configs to SQLite? Validate before read/write?

**Answer: NO - Image configs are NOT cached.**

The [`get_image_config()`](app/modules/finders/config_manifest.py:12) function fetches configs directly from the registry every time. The SQLite database only stores:
- `layer_metadata` - layer digest, index, size, entry counts
- `layer_entries` - filesystem entries from peeked layers

**Gap identified:** Image configs (ENV vars, CMD, history, labels) are fetched on every request. Consider caching them if performance becomes an issue.

---

### Q2: Do we warn when carving without layer_index and no DB record?

**Answer: NO - There is no warning.**

The [`carve_file_to_bytes()`](app/modules/keepers/carver.py:553) function:
- If `layer_index=None`, it searches ALL layers (lines 605-606)
- There is no database lookup to check if the layer has been peeked
- The carver operates completely independently of the SQLite database

**Gap identified:** The carver does not consult the database at all. A user could carve from a layer they've never inspected, without any warning.

---

### Q3: Is there a mapping of idx to sha256 digest? Can users know if the next layer is out of range?

**Answer: PARTIAL - The mapping exists in SQLite but is not exposed to users.**

The `layer_metadata` table stores both `layer_index` and `layer_digest`:

| owner | repo | tag | layer_index | layer_digest |
|-------|------|-----|-------------|--------------|
| alpine | git | v2.52.0 | 0 | sha256:fb78f26... |
| alpine | git | v2.52.0 | 1 | sha256:e0018a9... |
| alpine | git | v2.52.0 | 2 | sha256:225ffaa... |

However:
1. **No API endpoint exposes layer count** - Users cannot know how many layers exist before accessing them
2. **Multi-arch images have duplicate indices** - Same owner/repo/tag/index can have different digests (different architectures)
3. **Out-of-range handling** - The carver returns an error message but there's no way to preemptively check

**Gap identified:** Need an endpoint like `/repositories/{ns}/{repo}/tags/{tag}/layers` that returns layer count and digest mapping.

---

## Recommended Next Steps

1. **Decide on caching strategy** for image configs (Q1)
2. **Add optional warning** when carving without layer index and no DB record (Q2)  
3. **Create layer listing endpoint** that exposes layer count and idx-to-digest mapping (Q3)
4. **Design TUI architecture** - the backend is ready, only the UI is missing