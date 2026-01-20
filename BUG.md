# BUG - Layer Peeking is catastrophically broken

"Layer Peeking" - verb; to infer the filesystem of an SOCI container image by scanning only the targz headers, not decompressing the entire image (only enough to get the peek) and then severing the connection immediately.

- Why? - By learning the file contents before hand it is easier to predict whether the container is even worth the time/space/effort to download.

---

## Problem Statement

- A programming agent with some bad assumptions broke layerpeek streaming; 
- The logic is corrupted and now the fies take a long time to download
    -  because the buffer is the wrong size, they fully decompress,
-  In short; they do NONE of the clever time saving hacks that this repository was designed to do.



- The first commit to sucessfully introduce layer peeking via file STREAMING is at this commit: [GitHub link to commit:](https://github.com/thesavant42/layerslayer/commit/9098b5be09e1215ff4deb107ace89205bbb90fb6)
    - Here is a diff link for you if that's easier. [diff](https://github.com/thesavant42/layerslayer/commit/9098b5be09e1215ff4deb107ace89205bbb90fb6.diff)

This is the commit that made things work.  **This commit modified `fetcher.py` and `layerslayer.py` for file stream "peeking".**


The architecture has shifted quite a bit, but the core technique of stream-peeking is still valid. Below is the formal documentation for the code *AT THIS STAGE*

## Constraints

There have been *MANY* code changes since then, I **cannot** simply revert to this state in Git time and start over.
- This information should be used for comparison to a "known good", and to repair the current code base.

## Diagrams & Docs
Links to Mermaid Charts in previous git commit:
- [fetcher-py mermaid chart](https://raw.githubusercontent.com/thesavant42/layerslayer/91d7635d2858ab778f277d6ff84220844b2ff3e1/docs/fetcher-py.md)

- [carver](https://raw.githubusercontent.com/thesavant42/layerslayer/91d7635d2858ab778f277d6ff84220844b2ff3e1/docs/carver-py.md)

- [layerslayer documentation and mermaid chart diagram](https://raw.githubusercontent.com/thesavant42/layerslayer/91d7635d2858ab778f277d6ff84220844b2ff3e1/docs/layerslayer-py.md)

- [TarParser doc](https://raw.githubusercontent.com/thesavant42/layerslayer/91d7635d2858ab778f277d6ff84220844b2ff3e1/docs/parser-tarparser.md)

## Open Questions:

Q: What are the substantial differences between the current code base's core modules and the "working" copy from the commit that made things work?
A:


Q: At what point did the current code base stop working? I first noticed on 01/19/2026
A:


Q: 
A:

## Goals:

1. Fix the bugs in file streaming peeking
2. Create unit tests for CI/CD
    1. Establish a base line of known-good and known-bad
    1. Create pipeline for Jenkins to run unit tests
        1. pull the git code
        1. run unit tests in a container w/ reports
        1. aggregate results and notify
        1. Build in safety valves so we dont bake in bad bugs.

## CI/CD TBD
- Tracked in the Wiki [here.](https://github.com/thesavant42/layerslayer/wiki/CI-CD-Requirements)
