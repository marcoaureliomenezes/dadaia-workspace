# Job folder

Holds the `wt-main` tree of one job and its `wt-task-<kkk>` trees.

`.dadaia/.venv/bin/dadaia worktree` manages this folder.
`new` writes this file when it creates the folder.
The last `merge` or `clean` below it removes the folder once only this file is left.
Do not put anything else here; a folder holding other files is left alone.
