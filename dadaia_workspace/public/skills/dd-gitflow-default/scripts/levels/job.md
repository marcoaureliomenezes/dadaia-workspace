# Job folder

Holds the `wt-main` tree of one job and its `wt-task-<kkk>` trees.
`.dadaia/.venv/bin/dadaia worktree` manages this folder: `new` writes this file, and the last merge or clean removes the folder once only this file is left.
