#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ask_bundle.py - CLI direkt ueber bundle.py (ohne laufenden Server / ohne fastmcp).

Fuehrt exakt denselben Such-Seam wie der MCP-Server aus (Bundle.search/get/register),
nur ohne die MCP-Transportschicht. Fuer Offline-Verifikation der User-Story-Antworten.

  python3 ask_bundle.py search "<query>" [thema=... gesetz=... jahr=... limit=...]
  python3 ask_bundle.py fetch "<id>"
  python3 ask_bundle.py register "<name>"      # z.B. rote-linien, nach-gesetz/solvency-ii
  python3 ask_bundle.py overview
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bundle import load_bundle

FIELDS = ("id", "title", "datum", "url", "dokumenttyp", "themen", "gesetzesbezug",
          "fachbereiche", "sprache", "description")


def _kw(args):
    return {k: v for a in args if "=" in a for k, v in [a.split("=", 1)]}


def main():
    a = sys.argv[1:]
    if not a:
        print("usage: search|fetch|register|overview", file=sys.stderr); return 2
    b = load_bundle()
    cmd = a[0]
    if cmd == "search":
        kw = _kw(a[2:])
        limit = int(kw.pop("limit", 10))
        hits = b.search(a[1], flt=kw or None, limit=limit)
        out = [{k: d[k] for k in FIELDS} for d in hits]
        print(json.dumps(out, ensure_ascii=False, indent=2))
    elif cmd == "fetch":
        d = b.get(a[1])
        if not d:
            print(f"not found: {a[1]}", file=sys.stderr); return 1
        print(json.dumps({k: d[k] for k in FIELDS}, ensure_ascii=False, indent=2))
        print("\n---BODY---\n")
        print(d["body"])
    elif cmd == "register":
        txt = b.register(a[1])
        print(txt if txt else f"no register: {a[1]}", file=sys.stderr if not txt else sys.stdout)
    elif cmd == "overview":
        print(b.overview())
    else:
        print(f"unknown: {cmd}", file=sys.stderr); return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
