## Code Structure: parser.py vs tar_parser.py

These two files serve **completely different purposes** despite similar names. Here's the analysis:

---

## parser.py - Manifest/Config Parser (32 lines)

**Purpose:** Parses Docker/OCI **manifest JSON** data structures for platform selection and layer enumeration.

### Structure
- 2 functions
- Imports from [`fetcher`](fetcher.py) module
- Works with **JSON data**

### parse_index (6-17)

```mermaid
flowchart TD
    START([index_json, image_ref, token]) --> PRINT[Print Available Platforms header]
    PRINT --> GET[Get manifests array from JSON]
    GET --> LOOP[For i, platform in manifests]
    LOOP --> EXTRACT[Extract os/architecture from platform dict]
    EXTRACT --> DISPLAY[Print platform index and info]
    DISPLAY --> MORE{more platforms?}
    MORE -->|Yes| LOOP
    MORE -->|No| INPUT[User input: select platform index]
    INPUT --> ACCESS[Access chosen platform by index]
    ACCESS --> GET_DIGEST[Extract digest from chosen]
    GET_DIGEST --> CALL[Call get_manifest_by_digest]
    CALL --> RETURN([return manifest])
```

### parse_manifest (19-32)

```mermaid
flowchart TD
    START([manifest_json]) --> GET[Get layers array from JSON]
    GET --> INIT[Initialize empty layer_info list]
    INIT --> PRINT[Print Layers header]
    PRINT --> LOOP[For idx, layer in layers]
    LOOP --> EXTRACT[Extract size and digest from layer dict]
    EXTRACT --> DISPLAY[Print index, digest, size in KB]
    DISPLAY --> APPEND[Append dict with digest/size to layer_info]
    APPEND --> MORE{more layers?}
    MORE -->|Yes| LOOP
    MORE -->|No| RETURN([return layer_info list])
```

### Branch Points

| Location | Condition | Branches |
|----------|-----------|----------|
| Line 10-12 | Loop iteration | Print each platform |
| Line 24-31 | Loop iteration | Process each layer |

---

## tar_parser.py - Binary Tar Header Parser (204 lines)

**Purpose:** Low-level **binary parsing** of 512-byte tar archive headers to extract file metadata without needing the complete tar file.

### Structure
- 1 dataclass ([`TarEntry`](tar_parser.py:15))
- 4 functions (3 private helpers + 1 public)
- Works with **raw bytes**
- Has explicit "DO NOT CHANGE" warning

### _mode_to_string (46-83)

```mermaid
flowchart TD
    START([mode_int, typeflag]) --> LOOKUP{typeflag in map?}
    LOOKUP -->|Yes| GET_CHAR[Get type character from map]
    LOOKUP -->|No| DEFAULT[Use - as default]
    GET_CHAR --> LOOP
    DEFAULT --> LOOP
    
    LOOP[For shift in 6,3,0] --> EXTRACT[Extract 3 bits at shift position]
    EXTRACT --> R{bit 4 set?}
    R -->|Yes| ADD_R[perms += r]
    R -->|No| ADD_RD[perms += -]
    ADD_R --> W{bit 2 set?}
    ADD_RD --> W
    W -->|Yes| ADD_W[perms += w]
    W -->|No| ADD_WD[perms += -]
    ADD_W --> X{bit 1 set?}
    ADD_WD --> X
    X -->|Yes| ADD_X[perms += x]
    X -->|No| ADD_XD[perms += -]
    ADD_X --> MORE{more shifts?}
    ADD_XD --> MORE
    MORE -->|Yes| LOOP
    MORE -->|No| RETURN([return type_char + perms])
```

### _parse_octal (86-94)

```mermaid
flowchart TD
    START([data bytes, default]) --> TRY{try}
    TRY --> STRIP[Strip null bytes and whitespace]
    STRIP --> EMPTY{stripped empty?}
    EMPTY -->|Yes| RET_DEFAULT([return default])
    EMPTY -->|No| PARSE[Parse as octal int]
    PARSE --> RET_VAL([return parsed value])
    TRY -->|ValueError/TypeError| RET_DEFAULT2([return default])
```

### _format_mtime (97-105)

```mermaid
flowchart TD
    START([unix_timestamp]) --> TRY{try}
    TRY --> NEG{timestamp <= 0?}
    NEG -->|Yes| RET_DASH([return dashes string])
    NEG -->|No| CONVERT[datetime.fromtimestamp]
    CONVERT --> FORMAT[strftime to string]
    FORMAT --> RETURN([return formatted])
    TRY -->|OSError/ValueError/OverflowError| RET_DASH2([return dashes string])
```

### parse_tar_header (108-204) - Main Function

```mermaid
flowchart TD
    START([data bytes, offset]) --> SIZE_CHK{offset + 512 > len data?}
    SIZE_CHK -->|Yes| RET_NONE([return None, -1])
    SIZE_CHK -->|No| SLICE[Extract 512-byte header]
    
    SLICE --> NULL_CHK{header is all null bytes?}
    NULL_CHK -->|Yes| RET_NONE2([return None, -1])
    NULL_CHK -->|No| MAGIC[Check magic at offset 257]
    
    MAGIC --> MAGIC_CHK{magic is ustar?}
    MAGIC_CHK -->|No| PASS[Continue anyway - might be old format]
    MAGIC_CHK -->|Yes| PARSE_NAME
    PASS --> PARSE_NAME
    
    PARSE_NAME[Parse name bytes 0-100] --> PREFIX_CHK{prefix bytes 345-500 not empty?}
    PREFIX_CHK -->|Yes| PREPEND[Prepend prefix to name]
    PREFIX_CHK -->|No| PARSE_FIELDS
    PREPEND --> PARSE_FIELDS
    
    PARSE_FIELDS[Parse mode, uid, gid, size, mtime, typeflag, linkname]
    PARSE_FIELDS --> TYPEFLAG_CHK{header byte 156 truthy?}
    TYPEFLAG_CHK -->|Yes| USE_CHAR[typeflag = chr of byte]
    TYPEFLAG_CHK -->|No| DEFAULT_TYPE[typeflag = 0]
    USE_CHAR --> DETERMINE
    DEFAULT_TYPE --> DETERMINE
    
    DETERMINE[Determine is_dir and is_symlink]
    DETERMINE --> IS_DIR{typeflag == 5 OR name ends with /?}
    IS_DIR --> IS_SYM{typeflag == 2?}
    IS_SYM --> MODE_STR[Generate mode string]
    MODE_STR --> CALC_NEXT[Calculate next_offset with 512-byte alignment]
    CALC_NEXT --> CREATE[Create TarEntry dataclass]
    CREATE --> RETURN([return entry, next_offset])
```

### Branch Points

| Location | Condition | Branches |
|----------|-----------|----------|
| Line 63-73 | `typeflag` in map | Return mapped char or default `-` |
| Line 78-81 | Permission bits | Add r/w/x or - for each position |
| Line 90-91 | Stripped data empty | Return default or parse |
| Line 93-94 | Parse exception | Return default |
| Line 100-101 | `timestamp <= 0` | Return dashes |
| Line 104-105 | Timestamp exception | Return dashes |
| Line 132-133 | Insufficient data | Return None, -1 |
| Line 138-139 | Null block (end of archive) | Return None, -1 |
| Line 143-145 | Magic check | Continue anyway if old format |
| Line 153-155 | Prefix exists | Prepend to filename |
| Line 174 | Typeflag byte truthy | Use char or default '0' |
| Line 181 | `typeflag == '5'` OR ends with `/` | Set is_dir |
| Line 182 | `typeflag == '2'` | Set is_symlink |

---

## Key Differences

| Aspect | parser.py | tar_parser.py |
|--------|-----------|---------------|
| **Purpose** | Parse Docker manifest JSON | Parse binary tar headers |
| **Input Type** | Python dict (from JSON) | Raw bytes |
| **Output** | Layer info dicts | TarEntry dataclass |
| **Level** | High-level API interaction | Low-level byte manipulation |
| **Dependencies** | Imports from fetcher.py | Self-contained |
| **User Interaction** | Has input() prompts | Pure parsing, no I/O |
| **Lines of Code** | 32 | 204 |
| **Complexity** | Simple dict access | Binary protocol parsing |

## Relationship in the Codebase

```mermaid
flowchart TD
    subgraph HighLevel["High-Level Manifest Parsing"]
        PARSER[parser.py]
        FETCHER[fetcher.py]
    end
    
    subgraph LowLevel["Low-Level Tar Parsing"]
        TAR_PARSER[tar_parser.py]
    end
    
    subgraph Consumers["Consumer Modules"]
        CARVER[carver.py]
        LAYERSLAYER[layerslayer.py]
    end
    
    PARSER -->|uses| FETCHER
    FETCHER -->|imports TarEntry, parse_tar_header| TAR_PARSER
    CARVER -->|imports TarEntry, parse_tar_header| TAR_PARSER
    LAYERSLAYER -->|uses| FETCHER
    LAYERSLAYER -->|uses| CARVER
```

**Summary:**
- [`parser.py`](parser.py) handles **what's in the Docker image** at the manifest level (platforms, layers)
- [`tar_parser.py`](tar_parser.py) handles **what's inside each layer** at the binary tar archive level (files, directories, permissions)