# Task: Research duplicate directories

## Problem Statement: Directories that have been superceded are displayewd alongside their duplicates, even though there's no actual difference in content.

![duplicatedirectories](/plans/screen.png)


### Background: OCI Uses overlay-fs and merges several .tar.gz images to create a merged image. This means that files and directories are overwritten by later layers. As a researcher, I want to compare the different versions of files and directories. But I do not need duplicate directories.


### Reasoning: When I click a folder from one layer, the view is the same as any other. If I view bin/ from Layer 19, the contents of bin/ will include the contents of all previous layers bin/ contents. That means the directories printed over and over is duplicated needlessly.

These are the directories from the combined view of the / folder in the screenshot linnked above:

```text
NAME
bin/
bin/
bin/
etc/
etc/
etc/
etc/
etc/
etc/
etc/
etc/
etc/
etc/
etc/
etc/
etc/
etc/
lib/
lib/
lib/
lib/
root/
tmp/
tmp/
tmp/
tmp/
tmp/
tmp/
tmp/
tmp/
tmp/
usr/
usr/
usr/
usr/
usr/
usr/
usr/
```

### Proposed Solution: When representing directories, only the highest-level layer number needs to be displayed; the earlier layers are implied. 

Based on my analysis of the code and the plan, I have a clear understanding of the problem:

Problem: In the merged/combined view of the FS Simulator, directories that exist in multiple layers are shown as duplicate entries. For example, etc/ appears 14 times because it exists in 14 different layers.

Root Cause: The fslog API returns all entries from all layers when in merged mode (self.fs_layer is None). The frontend (app/tui/app.py) simply displays all entries returned by the API without deduplication.

Key Insight from plan.md: "When representing directories, only the highest-level layer number needs to be displayed; the earlier layers are implied."

This is logically sound because:

In overlay-fs, when you browse a directory, you see the merged contents of all layers
Clicking on bin/ from L4 shows the same content as clicking on bin/ from L19 - the merged view
Therefore, showing bin/ 3 times adds no value and clutters the UI

Based on my analysis of _do_load_fslog(), the merged view duplication happens in the TUI when it adds all entries to the DataTable without deduplication. The fix would be to deduplicate directories (keeping only the highest layer) before adding rows

The Problem
In _do_load_fslog(), when displaying the merged view (all layers), the code iterates through all lines returned by the API and adds every entry directly to the table without any deduplication:

for line in lines:
    entry = parse_fslog_line(line)
    if entry:
        fs_table.add_row(
            entry["mode"],
            entry["size"],
            entry["date"],
            entry["name"],
            entry.get("layer", "")
        )

This results in directories like etc/ appearing 14 times (once per layer that contains it).

The Fix
The fix is straightforward - add deduplication logic that keeps only the highest layer number for each directory name. The logic should:

Parse all entries from the API response
For entries that are directories (name ends with /), track only the entry with the highest layer number
For files (non-directories), keep all entries as they represent different versions
Add rows to the table with directories deduplicated
Suggested Action