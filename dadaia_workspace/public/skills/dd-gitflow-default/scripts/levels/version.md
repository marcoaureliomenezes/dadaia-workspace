# Version folder

Holds the rc folders and the lanes (`wt-backlog-<slug>`, `wt-hotfix-<bug-id>`) of one release version.
`dadaia worktree` manages this folder: `new` writes this file, and the last merge or clean removes the folder once only this file is left.
