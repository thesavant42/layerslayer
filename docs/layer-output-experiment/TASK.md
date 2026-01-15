# Task: Store and Print Layer Peek data

Task 1 is complete!

# Phase 2

I need a way to navigate the virtual directory structure. To do this, a basic textual datable makes the most sense

fs_faker.py output:

```bash
python .\fs_faker.py layer-0.txt "/"

drwxr-xr-x       0.0 B  2025-12-16 23:03  bin/
drwxr-xr-x       0.0 B  2025-12-16 23:03  dev/
drwxr-xr-x       0.0 B  2025-12-16 23:03  etc/
drwxr-xr-x       0.0 B  2025-12-16 23:03  home/
drwxr-xr-x       0.0 B  2025-12-16 23:03  lib/
drwxr-xr-x       0.0 B  2025-12-16 23:03  media/
drwxr-xr-x       0.0 B  2025-12-16 23:03  mnt/
drwxr-xr-x       0.0 B  2025-12-16 23:03  opt/
drwxr-xr-x       0.0 B  2025-12-16 23:03  proc/
drwx------       0.0 B  2025-12-16 23:03  root/
drwxr-xr-x       0.0 B  2025-12-16 23:03  run/
drwxr-xr-x       0.0 B  2025-12-16 23:03  sbin/
drwxr-xr-x       0.0 B  2025-12-16 23:03  srv/
drwxr-xr-x       0.0 B  2025-12-16 23:03  sys/
drwxrwxrwx       0.0 B  2025-12-16 23:03  tmp/
drwxr-xr-x       0.0 B  2025-12-16 23:03  usr/
drwxr-xr-x       0.0 B  2025-12-16 23:03  var/
                                                    #...continues
```

- Equivalent output to `ls -la /etc`

```bash
python .\fs_faker.py layer-0.txt "etc/"
                                          ..   
-rw-r--r--       7.0 B  2025-12-16 23:02  alpine-release
drwxr-xr-x       0.0 B  2025-12-16 23:03  apk/
drwxr-xr-x       0.0 B  2025-12-16 23:03  busybox-paths.d/
drwxr-xr-x       0.0 B  2025-12-16 23:03  crontabs/
-rw-r--r--      89.0 B  2025-11-29 02:44  fstab
-rw-r--r--     510.0 B  2025-11-29 02:44  group
-rw-r--r--      10.0 B  2025-11-29 02:44  hostname
-rw-r--r--      79.0 B  2025-11-29 02:44  hosts
-rw-r--r--     570.0 B  2025-11-29 02:44  inittab
-rw-r--r--      51.0 B  2025-12-16 23:02  issue
drwxr-xr-x       0.0 B  2025-12-16 23:03  logrotate.d/
drwxr-xr-x       0.0 B  2025-12-16 23:03  modprobe.d/
-rw-r--r--      15.0 B  2025-11-29 02:44  modules
drwxr-xr-x       0.0 B  2025-12-16 23:03  modules-load.d/
-rw-r--r--     284.0 B  2025-11-29 02:44  motd
lrwxrwxrwx       0.0 B  2025-12-16 23:03  mtab -> ../proc/mounts
drwxr-xr-x       0.0 B  2025-12-16 23:03  network/
-rw-r--r--     205.0 B  2025-11-29 02:44  nsswitch.conf
drwxr-xr-x       0.0 B  2025-12-16 23:03  opt/
lrwxrwxrwx       0.0 B  2025-12-16 23:03  os-release -> ../usr/lib/os-release
-rw-r--r--     702.0 B  2025-11-29 02:44  passwd
drwxr-xr-x       0.0 B  2025-12-16 23:03  periodic/
-rw-r--r--     547.0 B  2025-11-29 02:44  profile
drwxr-xr-x       0.0 B  2025-12-16 23:03  profile.d/
-rw-r--r--      3.1 KB  2025-11-29 02:44  protocols
drwxr-xr-x       0.0 B  2025-12-16 23:03  secfixes.d/
-rw-r--r--     156.0 B  2025-12-16 06:19  securetty
-rw-r--r--     12.5 KB  2025-11-29 02:44  services
-rw-r-----     260.0 B  2025-12-16 23:03  shadow
-rw-r--r--      38.0 B  2025-11-29 02:44  shells
drwxr-xr-x       0.0 B  2025-12-16 23:03  ssl/
drwxr-xr-x       0.0 B  2025-12-16 23:03  ssl1.1/
-rw-r--r--      53.0 B  2025-11-29 02:44  sysctl.conf
drwxr-xr-x       0.0 B  2025-12-16 23:03  sysctl.d/
drwxr-xr-x       0.0 B  2025-12-16 23:03  udhcpc/
```

- `ls -la /etc/apk/`

```bash
python .\fs_faker.py layer-0.txt "etc/apk/"

-rw-r--r--       7.0 B  2025-12-16 23:03  arch
drwxr-xr-x       0.0 B  2025-12-16 23:03  keys/
drwxr-xr-x       0.0 B  2025-12-16 23:03  protected_paths.d/
-rw-r--r--     103.0 B  2025-12-16 23:03  repositories
-rw-r--r--      74.0 B  2025-12-16 23:03  world
```


[`fs_faker.py`](docs/layer-output-experiment/fs_faker.py) already has all the directory navigation logic:
**fs_faker.py stays untouched - it's the reference implementation.**
- [`normalize_path()`](docs/layer-output-experiment/fs_faker.py:66) - path normalization
- [`get_parent_path()`](docs/layer-output-experiment/fs_faker.py:83) - for ".." navigation  
- [`get_entry_name()`](docs/layer-output-experiment/fs_faker.py:101) - extract display name
- [`get_direct_children()`](docs/layer-output-experiment/fs_faker.py:121) - filter to current directory
- [`format_entry()`](docs/layer-output-experiment/fs_faker.py:145) - ls -la style output

Phase 2 is just: wrap this existing logic in a Textual DataTable that queries SQLite instead of reading a log file.
**fs_faker.py stays untouched - it's the reference implementation.**
1. Query `layer_entries` from SQLite instead of parsing a log file
2. Display in a Textual DataTable with zebra stripes and row cursor
3. Handle Enter key to navigate into directories (using existing `get_direct_children()` logic)
4. Add ".." row when not at root (using existing `get_parent_path()`)
5. Enable sorting via column headers

The navigation logic already exists in fs_faker.py. Just need to swap the data source from file to SQLite and add the Textual UI wrapper.

### Displaying and navigating via a Textual dataTable
- https://textual.textualize.io/widgets/data_table/

### Make the rows easier to read
- https://textual.textualize.io/widgets/data_table/#textual.widgets.DataTable(zebra_stripes) true

### Enable Sorting
- https://textual.textualize.io/widgets/data_table/#sorting

### Use a Row cursor
https://textual.textualize.io/widgets/data_table/#textual.widgets.DataTable.cursor_row

Print out the filesystem, using patterns for print info used by [the FS Faker experiment](docs\layer-output-experiment\fs-faker-results.md)
- Allow the page to scroll 
- **do not prohibit the columns from stretching to avoid overflow or wrapping**.
- render ".."  to allow reverse directory traversal
