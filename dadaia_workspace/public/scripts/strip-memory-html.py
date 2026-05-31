#!/usr/bin/env python3
"""Strip <head>, <style>, and Mermaid <script> blocks from a memory HTML file.

Usage: python3 strip-memory-html.py <file.html>
Output: stripped HTML on stdout (prose, headings, tables, mermaid blocks preserved).
Exit 1 silently if file is missing or unreadable.
"""

import sys
from html.parser import HTMLParser

# HTML void elements (no closing tag) — do not track depth for these.
_VOID = frozenset(
    [
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    ]
)
# Block-level containers to skip entirely (tag + all descendants).
_SKIP_CONTAINERS = frozenset(["head", "style"])


class MemoryHtmlStripper(HTMLParser):
    """Remove <head>, <style>, and Mermaid <script> blocks; preserve everything else.

    Preserves all prose, headings, tables, and Mermaid diagram text
    (<pre class="mermaid"> / <div class="mermaid">).
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        # Stack of skip-container tag names currently open.
        self._skip_stack: list[str] = []
        self._mermaid_script = False  # inside a mermaid CDN / init <script>
        self.output: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # Inside a skipped container: track nesting but emit nothing.
        if self._skip_stack:
            if tag not in _VOID:
                self._skip_stack.append(tag)
            return

        # Start a new skip block.
        if tag in _SKIP_CONTAINERS:
            self._skip_stack.append(tag)
            return

        # Skip Mermaid <script src="…mermaid…"> and inline mermaid.initialize() scripts.
        if tag == "script":
            attr_dict = dict(attrs)
            src = attr_dict.get("src", "")
            if "mermaid" in (src or "") or not src:
                self._mermaid_script = True
                return

        # Emit the tag with attributes.
        if attrs:
            parts = []
            for name, val in attrs:
                parts.append(name if val is None else f'{name}="{val}"')
            self.output.append(f"<{tag} {' '.join(parts)}>")
        else:
            self.output.append(f"<{tag}>")

    def handle_endtag(self, tag: str) -> None:
        if self._skip_stack:
            # Pop when we close the innermost skip container.
            if self._skip_stack and self._skip_stack[-1] == tag:
                self._skip_stack.pop()
            return
        if self._mermaid_script and tag == "script":
            self._mermaid_script = False
            return
        self.output.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if self._skip_stack or self._mermaid_script:
            return
        self.output.append(data)

    def handle_entityref(self, name: str) -> None:
        if self._skip_stack or self._mermaid_script:
            return
        self.output.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self._skip_stack or self._mermaid_script:
            return
        self.output.append(f"&#{name};")

    def get_output(self) -> str:
        return "".join(self.output)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(1)
    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except (FileNotFoundError, OSError):
        sys.exit(1)
    parser = MemoryHtmlStripper()
    parser.feed(content)
    sys.stdout.write(parser.get_output())


if __name__ == "__main__":
    main()
