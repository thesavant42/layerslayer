# Task: Store and Print Layer Peek data
[fs-log-sqlite.py](fs-log-sqlite.py) is a fork of fs-log-sqlite.py, which takes the text logs from layer-peekiing docker containers, and filters their output to the queried directories, while not showing subdirectories

- Update the fs-log-sqlite.py to use the sqlite file instead of a flat text file.

### Background

The result is output similar to `ls -la` in a linux terminal.
Examples:

fs-log-sqlite.py output:

```bash
python .\fs-log-sqlite.py "ubuntu:24.04" "/"

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
                                                    #...continues
```

- Equivalent output to `ls -la /etc`

```bash
python .\fs-log-sqlite.py "ubuntu:24.04" "etc/"
                                          ..   
-rw-r--r--       7.0 B  2025-12-16 23:02  alpine-release
drwxr-xr-x       0.0 B  2025-12-16 23:03  apk/
drwxr-xr-x       0.0 B  2025-12-16 23:03  busybox-paths.d/
drwxr-xr-x       0.0 B  2025-12-16 23:03  crontabs/
-rw-r--r--      89.0 B  2025-11-29 02:44  fstab
drwxr-xr-x       0.0 B  2025-12-16 23:03  modprobe.d/
-rw-r--r--      15.0 B  2025-11-29 02:44  modules
drwxr-xr-x       0.0 B  2025-12-16 23:03  modules-load.d/
-rw-r--r--     284.0 B  2025-11-29 02:44  motd
lrwxrwxrwx       0.0 B  2025-12-16 23:03  mtab -> ../proc/mounts
[...]
```

- Equivalent to `ls -la /etc/apk/`

```bash
python .\fs-log-sqlite.py "ubuntu:24.04" "etc/apk/"

-rw-r--r--       7.0 B  2025-12-16 23:03  arch
drwxr-xr-x       0.0 B  2025-12-16 23:03  keys/
drwxr-xr-x       0.0 B  2025-12-16 23:03  protected_paths.d/
-rw-r--r--     103.0 B  2025-12-16 23:03  repositories
-rw-r--r--      74.0 B  2025-12-16 23:03  world
```



[fs-log-sqlite.py](fs-log-sqlite.py) Is the file to update: It should instead connect to the sqlite database at [fs-log-sqlite.db](fs-log-sqlite.db)
