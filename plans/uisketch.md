

+-----------------------------------------------------------------------+
|  HEADER               		 			                            | - Textual Header
+-----------------------------------------------------------------------+
|  Namespace / REPO Description,		  [SEARCH]  [DROPDOWN FOR TAGS] | - Textual Placeholder panel, Approximately 3 rows tall
+-----------------------------------+-----------------------------------+
|  PAN 1: LAYERS LIST (35% Width)   |  PAN 2: COMMAND DETAIL (65% Width)| - Two side-by-side panels
|                                   |                                   |    - PAN 1 (left) 35%w
|  [Selected] 1. ADD alpine...      |  +-----------------------------+  |    - PAN 2 (right) 65%w
|  [ ]        2. CMD ["/bin/sh"]    |  | FILE SYSTEM                 |  | - Panels are widgets, can be switched with content-switch widgets
|  [ ]        3. RUN ...            |  |                             |  |
|  [ ]        4. ...                |  | SIMULATED HERE              |  |
|                                   |  |                             |  |
|                                   |  +-----------------------------+  |
|                                   |                                   |
+-----------------------------------+-----------------------------------+
|  FOOTER Hotkeys Debug                                                 |
+-----------------------------------------------------------------------+

TOP: Textual Header Row With Widget

Beneath TOP: Placeholder panel that stretches the entire width 100w of the display area
- Should contain a search box, for /search.data?
- Drop-down text selector widget that is programatically populated when a reopository is selected after searching
    - 1. `/search.data?q=query` for `query`, `repository`, results populate `PAN 2`
    - 2. Select a Repo from `PAN 2` triggers a call to `/repositories/namespace/repo/tags/tag` api endpoint, sorted most recent first and populates the dropdown for tags.
    - 3. Panel 1 (`PAN1`) Populates with the Image Config Manifest [^1], That flows top down, with VERTICAL Scrolling for the whole COL 1 Panel
    - 4. Picking a layer on `PAN 1` displays the `/fslog` output for that idx[] value on `PAN 2` in a data table with output for the "/" path of the simulated filesystem. 
        - "empty layers" have no files but still have Build instructions and other metadata
    - 5. I can navigate the subdirectories of the filesystem with the row cursor, and when I select a row with enter I can enter the folder if it's a directory, or carve the file if it's not.
        - Prompt the user: 
            - 1. Carve this file? y/N?
            - 2. Save or Stream? (stream the file btes or render as plain text)
    - 6. File contents are saved or displayed.