You work in the dadaia workspace at `/workspace`; its project `demo` is the repo `/workspace/repos/demo`.

The suite of `demo`'s work branch `feature/0.1.0` (its CI: `python3 -m unittest discover -s tests`) is red since the merge of `strip-punctuation`: `slug()` no longer lowercases, which `README.md` documents.

The operator confirms: this is a bug, and it blocks the release. Register it and fix it now, on `feature/0.1.0`, following the workspace's law.
