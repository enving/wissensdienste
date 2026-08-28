"""mcp_ask.py - tiny CLI over the running MCP server (for testing/verification).

Talks to the server via the actual MCP protocol (fastmcp Client), so it exercises
the same path an assistant connector would. Every call goes through the server's
tools; nothing reads the bundle files directly.

Usage (needs a Python env with `fastmcp` installed; MCP_URL defaults to local):
  python mcp_ask.py search "<query>" [thema=... gesetz=... jahr=... limit=...]
  python mcp_ask.py fetch "<id>"
  python mcp_ask.py list [thema=... gesetz=... ...]
  python mcp_ask.py register "<name>"        # e.g. nach-gesetz/solvency-ii, rote-linien
  python mcp_ask.py overview
"""
import asyncio
import json
import os
import sys

from fastmcp import Client

URL = os.environ.get("MCP_URL", "http://localhost:8000/mcp")


def _kw(args):
    return {k: v for a in args if "=" in a for k, v in [a.split("=", 1)]}


async def main():
    a = sys.argv[1:]
    if not a:
        print("usage: search|fetch|list|register|overview", file=sys.stderr)
        return 2
    cmd = a[0]
    async with Client(URL) as c:
        if cmd == "search":
            payload = {"query": a[1], **_kw(a[2:])}
            if "limit" in payload:
                payload["limit"] = int(payload["limit"])
            r = await c.call_tool("search", payload)
        elif cmd == "fetch":
            r = await c.call_tool("fetch", {"id": a[1]})
        elif cmd == "list":
            r = await c.call_tool("list_documents", _kw(a[1:]))
        elif cmd == "register":
            r = await c.call_tool("get_register", {"name": a[1]})
        elif cmd == "overview":
            r = await c.call_tool("get_overview", {})
        else:
            print(f"unknown command: {cmd}", file=sys.stderr)
            return 2
        data = getattr(r, "structured_content", None)
        if data is None:
            data = getattr(r, "data", None)
        print(json.dumps(data if data is not None else str(r), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
