# Terminal-style format experiments

## Summary of Your Goals
Problem: Docker layer filesystem logs are stored as flat text showing every file, directory, and symlink. The complete output is a wall of text that's hard to work with.


Solution: Build a virtual filesystem navigator - a Python script that filters the log to show only the contents of a specific directory path, simulating the experience of navigating with cd and ls -la.

### Plan
Immediate Task: Create fs_faker.py that:

- Takes a log filename and a virtual path as arguments
**Direct Children Only**: For path `/`, show `bin/`, `dev/`, `etc/` but not `bin/arch`, `etc/apk/`, etc.


**Preserve the log's formatting, it will be finalized in a later step.**

 **Path Parsing**: Extract the path component (last field) from each line, then filter for entries where the parent directory matches the requested path.

**Handling Root**: Since paths in [`layer-0.txt`](layer-output-experiment/layer-0.txt) start with `bin/` rather than `/bin/`, you'll need to either:
   - Treat no leading slash as relative to root
   - Prepend `/` conceptually when interpreting paths

The concept is solid - you're building a simple query interface over structured text data.

Logs of filesystem are stored in a consistent format, as demonstrated by this snippet, which shows a portion of a log.

Snippet from [layer-0.txt](layer-0.txt)

```bash
[...continuing from above...]
  lrwxrwxrwx     0    0     0.0 B  2025-12-16 23:03  bin/usleep -> /bin/busybox
  lrwxrwxrwx     0    0     0.0 B  2025-12-16 23:03  bin/watch -> /bin/busybox
  lrwxrwxrwx     0    0     0.0 B  2025-12-16 23:03  bin/zcat -> /bin/busybox
  drwxr-xr-x     0    0     0.0 B  2025-12-16 23:03  dev/
  drwxr-xr-x     0    0     0.0 B  2025-12-16 23:03  etc/
  -rw-r--r--     0    0     7.0 B  2025-12-16 23:02  etc/alpine-release
  drwxr-xr-x     0    0     0.0 B  2025-12-16 23:03  etc/apk/
  -rw-r--r--     0    0     7.0 B  2025-12-16 23:03  etc/apk/arch
  drwxr-xr-x     0    0     0.0 B  2025-12-16 23:03  etc/apk/keys/
  -rw-r--r--     0    0   451.0 B  2025-09-18 10:13  etc/apk/keys/alpine-devel@lists.alpinelinux.org-4a6a0840.rsa.pub
  -rw-r--r--     0    0   451.0 B  2025-09-18 10:13  etc/apk/keys/alpine-devel@lists.alpinelinux.org-5261cecb.rsa.pub
  -rw-r--r--     0    0   800.0 B  2025-09-18 10:13  etc/apk/keys/alpine-devel@lists.alpinelinux.org-6165ee59.rsa.pub
  drwxr-xr-x     0    0     0.0 B  2025-12-16 23:03  etc/apk/protected_paths.d/
  -rw-r--r--     0    0   103.0 B  2025-12-16 23:03  etc/apk/repositories
  -rw-r--r--     0    0    74.0 B  2025-12-16 23:03  etc/apk/world
  drwxr-xr-x     0    0     0.0 B  2025-12-16 23:03  etc/busybox-paths.d/
  -rw-r--r--     0    0    3.9 KB  2025-12-16 06:19  etc/busybox-paths.d/busybox
 [...continues...]
```

All of the files, directories, and symmbolic links for the filesystem of each layer are displayed.
While great data to have, the wall of text output is not useful. 

What I would like is the output to be filtered dynaimcally, according to this workflow outline:

- Assumptions: In this example we will focus on a single layer and assume the entire filesystem is present

## Simulated 'ls -la' Terminal navigation

Terminal output should be limited to only displaying the contents of a specific directory, as though I typed `ls -la` in the terminal.
- Beginning with the container's root directory, `/` in Linux, which we will assume in this example. This would be equivalent to `cd /; ls -la;`



### Viewing the / Directory

Beginning at the os root makes sense. Limiting the output to just the root's contents is a much more manageable task. 

```bash
savant42@REPOSITORYNAME:/$ cd /; ls -la;    # this part is a simulation, a hardcoded prompt since this is not able to execute commands

drwxr-xr-x  28 root root    4096 Jan 14 08:47 .
drwxr-xr-x  28 root root    4096 Jan 14 08:47 ..
drwxr-xr-x   3 root root    4096 Nov 26 18:18 Docker
lrwxrwxrwx   1 root root       7 Apr 22  2024 bin -> usr/bin
drwxr-xr-x   2 root root    4096 Feb 26  2024 bin.usr-is-merged
drwxr-xr-x   2 root root    4096 Apr 22  2024 boot
drwxr-xr-x  15 root root    3940 Jan 14 08:47 dev
drwxr-xr-x  95 root root    4096 Jan 14 13:01 etc
drwxr-xr-x   3 root root    4096 Nov 26 18:08 home
-rwxrwxrwx   1 root root 2735264 Aug  6 12:54 init
lrwxrwxrwx   1 root root       7 Apr 22  2024 lib -> usr/lib
drwxr-xr-x   2 root root    4096 Apr  8  2024 lib.usr-is-merged
lrwxrwxrwx   1 root root       9 Apr 22  2024 lib64 -> usr/lib64
drwx------   2 root root   16384 Nov 26 17:53 lost+found
drwxr-xr-x   2 root root    4096 Aug  5 09:55 media
drwxr-xr-x   6 root root    4096 Dec 13 00:29 mnt
drwxr-xr-x   2 root root    4096 Aug  5 09:55 opt
dr-xr-xr-x 405 root root       0 Jan 14 08:47 proc
drwx------   5 root root    4096 Dec 18 23:17 root
drwxr-xr-x  20 root root     720 Jan 14 08:55 run
lrwxrwxrwx   1 root root       8 Apr 22  2024 sbin -> usr/sbin
drwxr-xr-x   2 root root    4096 Mar 31  2024 sbin.usr-is-merged
drwxr-xr-x   2 root root    4096 Nov 26 17:53 snap
drwxr-xr-x   2 root root    4096 Aug  5 09:55 srv
dr-xr-xr-x  13 root root       0 Jan 14 13:01 sys
drwxrwxrwt   8 root root    4096 Jan 14 13:01 tmp
drwxr-xr-x  12 root root    4096 Aug  5 09:55 usr
drwxr-xr-x  13 root root    4096 Nov 26 17:53 var
drwx------   2 root root    4096 Nov 29 22:29 wslGlHcAk
drwx------   2 root root    4096 Nov 29 22:29 wslMPlhKm
drwx------   2 root root    4096 Nov 29 22:29 wslMdICKm
drwx------   2 root root    4096 Nov 29 22:29 wslehMPJm
drwx------   2 root root    4096 Nov 29 22:29 wslmMcBHm
jbras@lilG:/$
```

In this example I decide after reving the output that I want to view `/etc`

Viewing `/etc/`

```bash
savant42@REPOSITORYNAME:/$ cd /etc; ls -la;

drwxr-xr-x 95 root root       4096 Jan 14 13:07 .
drwxr-xr-x 28 root root       4096 Jan 14 08:47 ..
-rw-------  1 root root          0 Aug  5 09:55 .pwd.lock
-rw-r--r--  1 root root        862 Aug  5 09:55 .resolv.conf.systemd-resolved.bak
-rw-r--r--  1 root root        208 Aug  5 09:55 .updated
drwxr-xr-x  2 root root       4096 Nov 26 18:09 PackageKit
drwxr-xr-x  7 root root       4096 Aug  5 09:57 X11
-rw-r--r--  1 root root       3444 Jul  5  2023 adduser.conf
[...continues...]
drwxr-xr-x  2 root root       4096 Aug  5 09:57 sgml
-rw-r-----  1 root shadow      801 Nov 26 18:08 shadow
-rw-r-----  1 root shadow      702 Aug  5 09:57 shadow-
-rw-r--r--  1 root root        132 Aug  5 09:57 shells
drwxr-xr-x  2 root root       4096 Aug  5 09:55 skel
drwxr-xr-x  3 root root       4096 Nov 26 18:09 ssh
drwxr-xr-x  4 root root       4096 Nov 26 18:09 ssl
-rw-r--r--  1 root root         19 Nov 26 18:08 subgid
-rw-r--r--  1 root root          0 Aug  5 09:55 subgid-
-rw-r--r--  1 root root         19 Nov 26 18:08 subuid
-rw-r--r--  1 root root          0 Aug  5 09:55 subuid-
-rw-r--r--  1 root root       4343 Apr  8  2024 sudo.conf
-rw-r--r--  1 root root       9804 Apr  8  2024 sudo_logsrvd.conf
-r--r-----  1 root root       1800 Jan 29  2024 sudoers
drwxr-xr-x  2 root root       4096 Aug  5 09:56 sudoers.d
[...continues...]

```

I can see that there's a `sudoers.d/` directory, and also some authentication materials listed. I navigate to the `sudoers.d` subdiretory.

Viewing `/etc/sudoers.d/`

```BASH
savant42@REPOSITORYNAME:/$ cd /etc/sudoers.d; ls -la;

drwxr-xr-x  2 root root 4096 Aug  5 09:56 .
drwxr-xr-x 95 root root 4096 Jan 14 13:07 ..
-r--r-----  1 root root 1068 Jan 29  2024 README
```

I decide I want to check out that `shadow` file, so I "traverse" up the directory tree by choosing the ".." characters twice, and return to the root directory. 
    - The ".." row will factor in  at a later step in this experiment, for now just know that it's there.

This example is contrived, but it demonstrates the ideal user flow.

Open Questions: 

Q - Is this a solved problem with third party python libraries?
A - 

Q - At present, we export the content as a flat text log, and print to standard out. If we store it as a machine-readable form like JSON can we reuse the file contents interactively and query the contents for reporting and searching?
A - 

## Task

Keep it simple, we are building an experiment a little bit at a time. Stay focused on this task only, we will get to the rest in order.

Task: python function to display the filesystem content, one directory at a time. 
1. Create a python script that takes two arguments:
    1. a file name example: "layer-0.txt"
    2. the virtual filesystem path , "/" as an example.

This is the first 5 lines of layer-0.txt tp serve as an example of the format:

```bash
jbras@lilG:/mnt/c/Users/jbras/GitHub/lsng/layer-output-experiment$ head -n 5 layer-0.txt
  drwxr-xr-x     0    0     0.0 B  2025-12-16 23:03  bin/
  lrwxrwxrwx     0    0     0.0 B  2025-12-16 23:03  bin/arch -> /bin/busybox
  lrwxrwxrwx     0    0     0.0 B  2025-12-16 23:03  bin/ash -> /bin/busybox
  lrwxrwxrwx     0    0     0.0 B  2025-12-16 23:03  bin/base64 -> /bin/busybox
  lrwxrwxrwx     0    0     0.0 B  2025-12-16 23:03  bin/bbconfig -> /bin/busybox
```
Example use case:

```bash
./fs_faker.py layer-0.txt "/"
```

When I run the script, I should see only the results for the root directory:
```bash

drwxr-xr-x  28 root root    4096 Jan 14 08:47 .
drwxr-xr-x  28 root root    4096 Jan 14 08:47 ..
drwxr-xr-x   3 root root    4096 Nov 26 18:18 Docker
lrwxrwxrwx   1 root root       7 Apr 22  2024 bin -> usr/bin
drwxr-xr-x   2 root root    4096 Feb 26  2024 bin.usr-is-merged
drwxr-xr-x   2 root root    4096 Apr 22  2024 boot
drwxr-xr-x  15 root root    3940 Jan 14 08:47 dev
drwxr-xr-x  95 root root    4096 Jan 14 13:01 etc
drwxr-xr-x   3 root root    4096 Nov 26 18:08 home
-rwxrwxrwx   1 root root 2735264 Aug  6 12:54 init
[...]
```

except the whole output of the contents of the "/" directory woud be displayed.

