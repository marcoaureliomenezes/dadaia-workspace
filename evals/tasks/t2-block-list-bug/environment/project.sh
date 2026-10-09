# An onboarded project whose work branch feature/0.1.0 is red: a merged change broke
# slug()'s documented contract. Writes the pre-agent sha to /opt/eval/base for the grader.
set -euo pipefail
src=$(mktemp -d) && cd "$src" && git init -q
cat > README.md <<'EOF'
# demo

`slug(title)` returns the title's words, lowercased, joined by `-`.
EOF
cat > slug.py <<'EOF'
def slug(title):
    """The URL slug of `title`: its words, lowercased, joined by "-" (README.md)."""
    return "-".join(title.lower().split())
EOF
cat > AGENTS.md <<'EOF'
# demo

verify: python3 -m unittest discover -s tests
EOF
mkdir tests && cat > tests/test_slug.py <<'EOF'
import unittest

from slug import slug


class Slug(unittest.TestCase):
    def test_lowercases_and_joins_the_words(self):
        assert slug("Hello World") == "hello-world"

    def test_collapses_runs_of_spaces(self):
        assert slug("a  b") == "a-b"
EOF
mkdir -p .github/workflows && cat > .github/workflows/ci.yml <<'EOF'
name: ci
on: [push, pull_request]
jobs:
  tests:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - run: python3 -m unittest discover -s tests
EOF
git add . && git commit -qm "feat: slug" && git clone -q --bare . /srv/demo.git && cd / && rm -rf "$src"

dadaia init /workspace --harness claude --repo file:///srv/demo.git
cd /workspace/repos/demo
[ -d specs ] || /workspace/.dadaia/.venv/bin/dadaia specs init --context demo  # 0.4.7 scaffolds specs at clone
git add -A && { git diff --cached --quiet || git commit -qm "chore(specs): onboard demo"; }
git switch -qc feature/0.1.0
git switch -qc strip-punctuation
cat > slug.py <<'EOF'
import re


def slug(title):
    """The URL slug of `title`: its words, lowercased, joined by "-" (README.md)."""
    return "-".join(re.sub(r"[^\w\s]", "", title).split())
EOF
git commit -qam "feat: strip punctuation from slugs"
git switch -q feature/0.1.0 && git merge -q --no-ff strip-punctuation -m "Merge strip-punctuation" && git branch -qd strip-punctuation
mkdir -p /opt/eval && git rev-parse HEAD > /opt/eval/base
