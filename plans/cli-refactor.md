# new submodule: cli.py

Problem statement: main.py:22-109 def parse_args()

- 87 lines of command line argument parsing in the main.py application entry point, which 

1 Violates Single Function principal
2. Come precariously close to the 100 loc style guide suggestion to refactor into submodules.

## Proposal: cli.py submodule

- Let's move the command line argument parsing to its own submodule

Task: refactor parse_args
- move the functions from main.py to app\modules\cli.py
- update imports