#!/usr/bin/env python3
"""okf_validate.py - check an Open Knowledge Format (OKF) bundle for conformance.

Python port of the skill's okf-validate.mjs (this environment has no Node), plus
the two graph checks the repo conventions in CLAUDE.md ask for.

Hard requirements (OKF v0.1). Any failure is an error and exits non-zero:
  - every non-reserved .md file opens with a YAML frontmatter block
  - every such block carries a non-empty `type` field
  - index.md carries no frontmatter, except the bundle-root index.md, which
    may carry frontmatter and, if it does, should declare okf_version

Soft guidance (warnings, never fail the bundle):
  - log.md date headings should be ISO 8601 YYYY-MM-DD
  - cross-links should resolve
  - concepts should not link to an index.md listing (dangling graph edge)
  - no orphan concepts (unless the bundle is a bulk corpus; pass --corpus)

Usage:  python3 okf_validate.py [bundle-dir] [--corpus]
"""
import os
import re
import sys

FM_RE = re.compile(r"^---\r?\n(.*?)\r?\n---", re.DOTALL)
HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LINK_RE = re.compile(r"\]\((/?[^)\s]+\.md)(?:#[^)]*)?\)")


def frontmatter(text):
    if text and text[0] == "﻿":
        text = text[1:]
    m = FM_RE.match(text)
    return m.group(1) if m else None


def field(fm, key):
    for line in fm.splitlines():
        if not line.strip() or line[:1].isspace():
            continue
        idx = line.find(":")
        if idx == -1:
            continue
        if line[:idx].strip() == key:
            return line[idx + 1:].strip()
    return None


def walk_md(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "node_modules"]
        for fn in filenames:
            if fn.endswith(".md"):
                out.append(os.path.join(dirpath, fn))
    return sorted(out)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    root = args[0] if args else "."
    corpus = "--corpus" in flags
    if not os.path.isdir(root):
        print(f"Not a directory: {root}", file=sys.stderr)
        sys.exit(2)

    def rel(p):
        return os.path.relpath(p, root).replace(os.sep, "/")

    errors, warnings = [], []
    files = walk_md(root)
    concepts = 0
    # graph bookkeeping: concept id -> has outbound / inbound concept link
    concept_ids = set()
    outbound = {}
    inbound = set()

    for f in files:
        name = os.path.basename(f)
        text = open(f, encoding="utf-8").read()
        fm = frontmatter(text)
        is_root_index = rel(f) == "index.md"

        if name == "index.md":
            if fm and not is_root_index:
                warnings.append(f"{rel(f)}: index.md should carry no frontmatter (only bundle-root may)")
            if fm and is_root_index and field(fm, "okf_version") is None:
                warnings.append(f"{rel(f)}: root index.md has frontmatter but does not declare okf_version")
            continue
        if name == "log.md":
            for m in HEADING_RE.finditer(text):
                if not ISO_RE.match(m.group(1)):
                    warnings.append(f'{rel(f)}: log heading "{m.group(1)}" is not ISO 8601 YYYY-MM-DD')
            continue

        concepts += 1
        cid = rel(f)[:-3]
        concept_ids.add(cid)
        if fm is None:
            errors.append(f"{rel(f)}: missing YAML frontmatter block")
            continue
        t = field(fm, "type")
        if t is None:
            errors.append(f"{rel(f)}: frontmatter has no 'type' field")
        elif t == "":
            errors.append(f"{rel(f)}: 'type' field is empty")

    # link checks
    for f in files:
        text = open(f, encoding="utf-8").read()
        name = os.path.basename(f)
        for m in LINK_RE.finditer(text):
            href = m.group(1)
            if re.match(r"^[a-z]+:", href, re.I):
                continue
            target = os.path.join(root, href.lstrip("/")) if href.startswith("/") else os.path.join(os.path.dirname(f), href)
            if not os.path.exists(target):
                warnings.append(f"{rel(f)}: link target not found -> {href}")
            # graph edges only from concept files
            if name not in ("index.md", "log.md"):
                tgt_rel = os.path.relpath(os.path.abspath(target), os.path.abspath(root)).replace(os.sep, "/")
                if tgt_rel.endswith("/index.md") or tgt_rel == "index.md":
                    warnings.append(f"{rel(f)}: concept links to an index listing (dangling graph edge) -> {href}")
                elif tgt_rel.endswith(".md"):
                    src = rel(f)[:-3]
                    outbound.setdefault(src, set()).add(tgt_rel[:-3])
                    inbound.add(tgt_rel[:-3])

    if not corpus:
        for cid in sorted(concept_ids):
            has_out = bool(outbound.get(cid))
            has_in = cid in inbound
            if not has_out and not has_in:
                warnings.append(f"{cid}.md: orphan concept (no inbound or outbound concept links)")

    for w in warnings:
        print(f"warn  {w}", file=sys.stderr)
    for e in errors:
        print(f"error {e}", file=sys.stderr)
    verdict = "NOT conformant." if errors else "Conformant."
    print(f'\nOKF v0.1 check of "{root}": {concepts} concept(s), '
          f"{len(errors)} error(s), {len(warnings)} warning(s). {verdict}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
