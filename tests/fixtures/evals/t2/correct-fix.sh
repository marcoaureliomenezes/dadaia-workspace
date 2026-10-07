# The law's shape on the planted bug: the record commit, then the fix; no test line removed.
set -e
cd /workspace/repos/demo
mkdir -p specs/bugs
echo '{"id": "slug-drops-lowercase", "ts": "2026-10-06T00:00:00Z", "reported_by": "plant", "title": "slug no longer lowercases", "severity": "HIGH", "surface": "slug", "component": "slug", "context": "demo", "symptom": "slug(\"Hello World\") returns Hello-World", "repro": "python3 -m unittest discover -s tests", "expected": "hello-world", "status": "open", "cause": null, "caused_by": null, "resolved_release": null, "audited": false, "closed_at": null}' >> specs/bugs/BUGS.jsonl
git add specs/bugs/BUGS.jsonl
git commit -qm "chore(bugs): report slug-drops-lowercase"
sed -i 's/"", title)/"", title.lower())/' slug.py
git commit -qam "fix(bugs): slug-drops-lowercase — restore the lowercase the README documents"
