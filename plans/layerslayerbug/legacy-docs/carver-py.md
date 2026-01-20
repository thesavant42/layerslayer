## Code Structure Overview for `carver.py`

The file contains:
- 2 constants ([`DEFAULT_CHUNK_SIZE`](carver.py:22), [`DEFAULT_OUTPUT_DIR`](carver.py:23))
- 4 dataclasses ([`ScanResult`](carver.py:30), [`CarveResult`](carver.py:40), [`LayerInfo`](carver.py:100))
- 3 classes ([`IncrementalGzipDecompressor`](carver.py:163), [`IncrementalBlobReader`](carver.py:201), [`TarScanner`](carver.py:276))
- 1 module-level session ([`_session`](carver.py:74))
- 5 functions ([`_fetch_pull_token()`](carver.py:81), [`_fetch_manifest()`](carver.py:108), [`extract_and_save()`](carver.py:346), [`carve_file()`](carver.py:378), [`main()`](carver.py:551))

## Module Organization

```mermaid
flowchart TD
    subgraph DataClasses["Data Classes (30-67, 100-105)"]
        SR[ScanResult]
        CR[CarveResult]
        LI[LayerInfo]
    end
    
    subgraph TokenMgmt["Token Management (74-93)"]
        SESSION[_session]
        FPT[_fetch_pull_token]
    end
    
    subgraph Manifest["Manifest Fetching (108-156)"]
        FM[_fetch_manifest]
    end
    
    subgraph Classes["Helper Classes"]
        IGD[IncrementalGzipDecompressor]
        IBR[IncrementalBlobReader]
        TS[TarScanner]
    end
    
    subgraph Extraction["Extraction (346-371)"]
        EAS[extract_and_save]
    end
    
    subgraph MainLogic["Main Carving (378-544)"]
        CF[carve_file]
    end
    
    subgraph CLI["CLI Entry (551-605)"]
        MAIN[main]
    end
    
    MAIN --> CF
    CF --> FPT
    CF --> FM
    CF --> IBR
    CF --> IGD
    CF --> TS
    CF --> EAS
    FM --> FPT
```

## Class Diagrams

```mermaid
classDiagram
    class IncrementalGzipDecompressor {
        +decompressor: zlib.decompressobj
        +buffer: bytes
        +bytes_decompressed: int
        +error: Optional[str]
        +__init__()
        +feed(compressed_data: bytes) bytes
        +get_buffer() bytes
    }
    
    class IncrementalBlobReader {
        +url: str
        +token: str
        +chunk_size: int
        +current_offset: int
        +bytes_downloaded: int
        +total_size: int
        +exhausted: bool
        +__init__(namespace, repo, digest, token, chunk_size)
        +fetch_chunk() bytes
    }
    
    class TarScanner {
        +target_path: str
        +entries_scanned: int
        +current_offset: int
        +__init__(target_path)
        -_normalize_path(path) str
        -_matches(entry_name) bool
        +scan(data: bytes) ScanResult
        +needs_more_data(buffer_size) bool
    }
```

## Main Function Control Flows

### _fetch_pull_token (81-93)

```mermaid
flowchart TD
    START([namespace, repo]) --> BUILD[Build auth_url]
    BUILD --> TRY{try}
    TRY -->|Success| REQ[requests.get]
    REQ --> RAISE[raise_for_status]
    RAISE --> RETURN([return token])
    TRY -->|RequestException| PRINT[Print error]
    PRINT --> RET_NONE([return None])
```

### _fetch_manifest (108-156)

flowchart TD
    START([namespace, repo, tag, token]) --> BUILD[Build URL and headers]
    BUILD --> TRY_REQ{try request}
    TRY_REQ -->|RequestException| ERR[Print error]
    ERR --> RET_EMPTY([return empty list])
    TRY_REQ -->|Success| GET_JSON[resp.json to manifest]
    
    GET_JSON --> CHECK_MEDIA{mediaType is multi-arch?}
    
    CHECK_MEDIA -->|No| EXTRACT_LAYERS
    CHECK_MEDIA -->|Yes| GET_LIST[Get manifests array]
    
    GET_LIST --> FIND_AMD64[Search for amd64/linux platform]
    FIND_AMD64 --> FOUND_AMD64{Found amd64/linux?}
    
    FOUND_AMD64 -->|Yes| SET_TARGET[target = matching manifest]
    FOUND_AMD64 -->|No| HAS_ANY{manifests array not empty?}
    
    HAS_ANY -->|Yes| USE_FIRST[target = first manifest]
    HAS_ANY -->|No| TARGET_CHECK
    
    SET_TARGET --> TARGET_CHECK
    USE_FIRST --> TARGET_CHECK
    
    TARGET_CHECK{target exists?}
    TARGET_CHECK -->|No| EXTRACT_LAYERS
    TARGET_CHECK -->|Yes| FETCH_DIGEST[Fetch manifest by target digest]
    FETCH_DIGEST --> UPDATE_MANIFEST[manifest = new response]
    UPDATE_MANIFEST --> EXTRACT_LAYERS
    
    EXTRACT_LAYERS[Extract layers from manifest]
    EXTRACT_LAYERS --> LOOP[For each layer in manifest.layers]
    LOOP --> CREATE[Create LayerInfo with digest, size, mediaType]
    CREATE --> APPEND[Append to layers list]
    APPEND --> MORE{more layers?}
    MORE -->|Yes| LOOP
    MORE -->|No| RETURN([return layers list])


### IncrementalGzipDecompressor.feed (175-190)

```mermaid
flowchart TD
    START([compressed_data]) --> EMPTY{data empty?}
    EMPTY -->|Yes| RET_EMPTY([return empty bytes])
    EMPTY -->|No| TRY{try decompress}
    TRY -->|Success| DECOMP[decompressor.decompress]
    DECOMP --> APPEND[buffer += decompressed]
    APPEND --> UPDATE[bytes_decompressed += len]
    UPDATE --> RET_DATA([return decompressed])
    TRY -->|zlib.error| SET_ERR[self.error = str e]
    SET_ERR --> RET_EMPTY2([return empty bytes])
```

### IncrementalBlobReader.fetch_chunk (222-269)

```mermaid
flowchart TD
    START(["self"]) --> EXHAUSTED{self.exhausted?}
    EXHAUSTED -->|Yes| RET_EMPTY([return empty bytes])
    EXHAUSTED -->|No| BUILD[Build Range header]
    BUILD --> TRY{try request}
    
    TRY -->|RequestException| PRINT_ERR[Print error]
    PRINT_ERR --> SET_EXHAUST1[self.exhausted = True]
    SET_EXHAUST1 --> RET_EMPTY2([return empty bytes])
    
    TRY -->|Success| CHECK_416{status == 416?}
    CHECK_416 -->|Yes| SET_EXHAUST2[self.exhausted = True] --> RET_EMPTY3([return empty bytes])
    CHECK_416 -->|No| RAISE[raise_for_status]
    
    RAISE --> CONTENT_RANGE{Content-Range has /?}
    CONTENT_RANGE -->|Yes| PARSE_SIZE[Parse total_size]
    CONTENT_RANGE -->|No| READ
    PARSE_SIZE --> READ[raw.read chunk_size]
    READ --> CLOSE[resp.close]
    
    CLOSE --> DATA_CHK{data empty?}
    DATA_CHK -->|Yes| SET_EXHAUST3[self.exhausted = True] --> RET_EMPTY4([return empty bytes])
    DATA_CHK -->|No| UPDATE[Update bytes_downloaded, current_offset]
    
    UPDATE --> END_CHK{reached total_size?}
    END_CHK -->|Yes| SET_EXHAUST4[self.exhausted = True]
    END_CHK -->|No| RET_DATA
    SET_EXHAUST4 --> RET_DATA([return data])
```

### TarScanner.scan (300-335)

```mermaid
flowchart TD
    START([data]) --> WHILE{offset + 512 <= len data?}
    WHILE -->|No| RET_NOT_FOUND([return ScanResult found=False])
    WHILE -->|Yes| PARSE[parse_tar_header]
    PARSE --> ENTRY_CHK{entry is None?}
    ENTRY_CHK -->|Yes| RET_NOT_FOUND
    ENTRY_CHK -->|No| INC[entries_scanned++]
    INC --> MATCH{_matches entry.name?}
    MATCH -->|Yes| RET_FOUND([return ScanResult found=True, entry, offsets])
    MATCH -->|No| OFFSET_CHK{next_offset > current_offset?}
    OFFSET_CHK -->|No| RET_NOT_FOUND
    OFFSET_CHK -->|Yes| UPDATE[current_offset = next_offset]
    UPDATE --> WHILE
```

### carve_file (378-544) - Main Carving Logic

```mermaid
flowchart TD
    START([image_ref, target_path, output_dir, chunk_size, verbose]) --> TIME[Start timer]
    TIME --> PARSE[parse_image_ref]
    
    PARSE --> V1{verbose?}
    V1 -->|Yes| PRINT1[Print fetching manifest]
    V1 -->|No| AUTH
    PRINT1 --> AUTH[_fetch_pull_token]
    
    AUTH --> TOK_CHK{token?}
    TOK_CHK -->|No| RET_ERR1([return CarveResult error: no token])
    TOK_CHK -->|Yes| MANIFEST[_fetch_manifest]
    
    MANIFEST --> LAYERS_CHK{layers?}
    LAYERS_CHK -->|No| RET_ERR2([return CarveResult error: no layers])
    LAYERS_CHK -->|Yes| V2{verbose?}
    V2 -->|Yes| PRINT2[Print layer count]
    V2 -->|No| LAYER_LOOP
    PRINT2 --> LAYER_LOOP
    
    LAYER_LOOP[For i, layer in layers] --> V3{verbose?}
    V3 -->|Yes| PRINT3[Print scanning layer]
    V3 -->|No| INIT
    PRINT3 --> INIT[Init reader, decompressor, scanner]
    
    INIT --> CHUNK_LOOP{reader.exhausted?}
    CHUNK_LOOP -->|Yes| NEXT_LAYER{more layers?}
    CHUNK_LOOP -->|No| FETCH[reader.fetch_chunk]
    
    FETCH --> COMPRESS_CHK{compressed empty?}
    COMPRESS_CHK -->|Yes| NEXT_LAYER
    COMPRESS_CHK -->|No| INC_CHUNK[chunks_fetched++]
    
    INC_CHUNK --> FIRST_CHUNK{first chunk?}
    FIRST_CHUNK -->|Yes| MAGIC{gzip magic 0x1f 0x8b?}
    FIRST_CHUNK -->|No| DECOMP
    MAGIC -->|No| V4{verbose?}
    V4 -->|Yes| PRINT_SKIP[Print not gzip] --> NEXT_LAYER
    V4 -->|No| NEXT_LAYER
    MAGIC -->|Yes| DECOMP[decompressor.feed]
    
    DECOMP --> DECOMP_ERR{decompressor.error?}
    DECOMP_ERR -->|Yes| V5{verbose?}
    V5 -->|Yes| PRINT_DECOMP_ERR[Print error] --> NEXT_LAYER
    V5 -->|No| NEXT_LAYER
    DECOMP_ERR -->|No| SCAN[scanner.scan buffer]
    
    SCAN --> V6{verbose?}
    V6 -->|Yes| PRINT_STATS[Print progress stats]
    V6 -->|No| FOUND_CHK
    PRINT_STATS --> FOUND_CHK{result.found?}
    
    FOUND_CHK -->|No| CHUNK_LOOP
    FOUND_CHK -->|Yes| NEED_MORE{need more data for content?}
    NEED_MORE -->|Yes| FETCH_MORE[Fetch more chunks until enough]
    NEED_MORE -->|No| EXTRACT_CHK
    FETCH_MORE --> EXTRACT_CHK{have full content?}
    
    EXTRACT_CHK -->|No| V7{verbose?}
    V7 -->|Yes| PRINT_INCOMPLETE[Print couldn't get full content]
    V7 -->|No| CHUNK_LOOP
    PRINT_INCOMPLETE --> CHUNK_LOOP
    
    EXTRACT_CHK -->|Yes| V8{verbose?}
    V8 -->|Yes| PRINT_FOUND[Print FOUND message]
    V8 -->|No| EXTRACT
    PRINT_FOUND --> EXTRACT[extract_and_save]
    EXTRACT --> CALC[Calculate elapsed, efficiency]
    CALC --> V9{verbose?}
    V9 -->|Yes| PRINT_DONE[Print stats]
    V9 -->|No| RET_SUCCESS
    PRINT_DONE --> RET_SUCCESS([return CarveResult found=True])
    
    NEXT_LAYER -->|Yes| V10{verbose?}
    V10 -->|Yes| PRINT_BLANK[Print blank line] --> LAYER_LOOP
    V10 -->|No| LAYER_LOOP
    NEXT_LAYER -->|No| ELAPSED[Calculate elapsed]
    ELAPSED --> V11{verbose?}
    V11 -->|Yes| PRINT_NOT_FOUND[Print file not found]
    V11 -->|No| RET_NOT_FOUND
    PRINT_NOT_FOUND --> RET_NOT_FOUND([return CarveResult found=False])
```

### extract_and_save (346-371)

```mermaid
flowchart TD
    START([data, content_offset, content_size, target_path, output_dir]) --> SLICE[Extract content from buffer]
    SLICE --> CLEAN[Clean path - remove leading slash]
    CLEAN --> BUILD[Build output_path]
    BUILD --> MKDIR[Create parent directories]
    MKDIR --> WRITE[Write bytes to file]
    WRITE --> RETURN([return path string])
```

### main (551-605) - CLI Entry

```mermaid
flowchart TD
    START([__main__]) --> PARSE[argparse.ArgumentParser]
    PARSE --> ADD_ARGS[Add image, filepath, output-dir, chunk-size, quiet args]
    ADD_ARGS --> PARSE_ARGS[parse_args]
    PARSE_ARGS --> CARVE[carve_file]
    CARVE --> EXIT{result.found?}
    EXIT -->|Yes| EXIT0([sys.exit 0])
    EXIT -->|No| EXIT1([sys.exit 1])
```

## Summary of Branch Points

| Location | Condition | Branches |
|----------|-----------|----------|
| Line 87-93 | `requests.get` exception | Return None or return token |
| Line 121-123 | `requests.get` exception in manifest | Return empty list |
| Line 127 | `mediaType` contains manifest.list/image.index | Multi-arch handling or direct extraction |
| Line 133-134 | Platform is amd64/linux | Set target or continue loop |
| Line 136-137 | No target found, manifests exist | Use first manifest as fallback |
| Line 139 | Target exists | Fetch by digest or skip |
| Line 180-190 | `zlib.error` in decompress | Set error and return empty |
| Line 226-227 | `self.exhausted` | Return empty or continue |
| Line 239-241 | HTTP 416 status | Mark exhausted |
| Line 247-248 | Content-Range has `/` | Parse total size |
| Line 253-255 | Data empty | Mark exhausted |
| Line 261-262 | Reached total_size | Mark exhausted |
| Line 266-269 | `RequestException` | Print error, mark exhausted |
| Line 310-312 | `entry is None` | Break scan loop |
| Line 317-325 | `_matches(entry.name)` | Return found result |
| Line 328-329 | `next_offset <= current_offset` | Break scan loop |
| Line 408/428/433... | `verbose` flag | Print progress or skip |
| Line 412-417 | Token fetch failed | Return error result |
| Line 421-426 | No layers found | Return error result |
| Line 447-448 | Compressed chunk empty | Break chunk loop |
| Line 453-457 | First chunk, not gzip | Skip layer |
| Line 462-465 | Decompression error | Break chunk loop |
| Line 475 | `result.found` | Extract file or continue scanning |
| Line 481-489 | Need more data for content | Fetch additional chunks |
| Line 492-526 | Have full content | Extract and return success |
| Line 527-530 | Incomplete content | Print warning, continue |

## Data Flow Through Components

```mermaid
flowchart LR
    subgraph Input
        IMG[Image Ref]
        PATH[Target Path]
    end
    
    subgraph Auth
        TOK[Token]
    end
    
    subgraph Manifest
        LAYERS[Layer List]
    end
    
    subgraph PerLayer["Per Layer Processing"]
        IBR2[IncrementalBlobReader]
        IGD2[IncrementalGzipDecompressor]
        TS2[TarScanner]
    end
    
    subgraph Output
        FILE[Extracted File]
        RESULT[CarveResult]
    end
    
    IMG --> TOK
    TOK --> LAYERS
    LAYERS --> IBR2
    IBR2 -->|compressed chunks| IGD2
    IGD2 -->|decompressed buffer| TS2
    TS2 -->|ScanResult| FILE
    FILE --> RESULT
    PATH --> TS2
```

The carving process uses an incremental streaming approach: it fetches compressed data in chunks via HTTP Range requests, decompresses on-the-fly, scans tar headers looking for the target file, and stops as soon as the target is fully extracted - avoiding downloading entire layers unnecessarily.