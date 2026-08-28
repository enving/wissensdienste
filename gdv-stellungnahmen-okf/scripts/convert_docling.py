#!/usr/bin/env python3
"""convert_docling.py - download GDV PDFs and convert them to Markdown via docling.

Reads GDV_Stellungnahmen/catalog.json. For each document:
  1. downloads the PDF to GDV_Stellungnahmen/pdf/<blob_id>.pdf  (host has internet)
  2. uploads it to the local docling-serve at /v1/convert/file    (container has none)
  3. strips image placeholders and writes GDV_Stellungnahmen/md/<blob_id>.md

Idempotent and incremental: an existing, non-empty .md is skipped, so re-running
after the scraper only processes new documents. Failures are logged and written to
GDV_Stellungnahmen/convert_failures.json for a targeted retry.

The download uses urllib; the docling upload shells out to curl (the multipart
form is simplest that way and this environment ships no `requests`).
"""
import concurrent.futures as cf
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..", "GDV_Stellungnahmen")
PDF_DIR = os.path.join(ROOT, "pdf")
MD_DIR = os.path.join(ROOT, "md")
CATALOG = os.path.join(ROOT, "catalog.json")
FAILURES = os.path.join(ROOT, "convert_failures.json")

DOCLING = os.environ.get("DOCLING_URL", "http://localhost:5001") + "/v1/convert/file"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) GDV-OKF-Ingest/1.0"
# docling-serve runs a single model worker; concurrent uploads OOM-crash it, so
# default to sequential. Transient crashes are retried (the container auto-restarts).
WORKERS = int(os.environ.get("WORKERS", "1"))
RETRIES = int(os.environ.get("RETRIES", "4"))

IMG_PLACEHOLDER = re.compile(r"^\s*<!-- image -->\s*$", re.MULTILINE)
MULTI_BLANK = re.compile(r"\n{3,}")


def download(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return True
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    if not data.startswith(b"%PDF"):
        raise ValueError("not a PDF (got HTML/redirect?)")
    with open(dest, "wb") as f:
        f.write(data)
    return True


def docling_markdown(pdf_path):
    # Table-structure extraction is on (proper Markdown tables). It is the memory-heavy
    # part of the pipeline and needs a roomy docling VM (>= ~6-8 GB); on a 3.8 GB VM it
    # OOM-crashes the single-worker container, so set TABLES=off there to linearize
    # tables to text instead. The timeout lets an OOM-mid-request fail rather than hang.
    tables = os.environ.get("TABLES", "on").lower() != "off"
    cmd = [
        "curl", "-s", "--max-time", "240", "-X", "POST", DOCLING,
        "-F", f"files=@{pdf_path};type=application/pdf",
        "-F", "to_formats=md",
        "-F", "image_export_mode=placeholder",
        "-F", "do_ocr=false",
        "-F", "include_images=false",
        "-F", f"do_table_structure={'true' if tables else 'false'}",
        "-F", f"table_mode={'accurate' if tables else 'fast'}",
    ]
    out = subprocess.run(cmd, capture_output=True, timeout=360)
    if out.returncode != 0:
        raise RuntimeError(f"curl failed: {out.stderr.decode()[:200]}")
    resp = json.loads(out.stdout.decode("utf-8", "ignore"))
    if resp.get("status") != "success":
        raise RuntimeError(f"docling status={resp.get('status')} errors={resp.get('errors')}")
    md = (resp.get("document") or {}).get("md_content") or ""
    if not md.strip():
        raise RuntimeError("empty markdown")
    md = IMG_PLACEHOLDER.sub("", md)
    md = MULTI_BLANK.sub("\n\n", md).strip() + "\n"
    return md


def process(doc):
    bid = doc["blob_id"]
    if not bid:
        return (doc, "skip", "no blob_id")
    md_path = os.path.join(MD_DIR, f"{bid}.md")
    if os.path.exists(md_path) and os.path.getsize(md_path) > 0:
        return (doc, "cached", None)
    pdf_path = os.path.join(PDF_DIR, f"{bid}.pdf")
    try:
        download(doc["pdf_url"], pdf_path)
    except Exception as e:
        return (doc, "fail", f"download: {e}")
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            md = docling_markdown(pdf_path)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md)
            return (doc, "ok", len(md))
        except Exception as e:
            last = str(e)
            time.sleep(3 * attempt)  # let the container recover / restart
    return (doc, "fail", f"after {RETRIES} tries: {last}")


def main():
    os.makedirs(PDF_DIR, exist_ok=True)
    os.makedirs(MD_DIR, exist_ok=True)
    docs = json.load(open(CATALOG, encoding="utf-8"))["documents"]
    only = sys.argv[1:]  # optional list of blob_ids to (re)process
    if only:
        docs = [d for d in docs if d["blob_id"] in set(only)]

    results = {"ok": 0, "cached": 0, "fail": 0, "skip": 0}
    failures = []
    total = len(docs)
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for i, (doc, status, info) in enumerate(ex.map(process, docs), 1):
            results[status] += 1
            tag = f"[{i}/{total}]"
            if status == "fail":
                failures.append({"blob_id": doc["blob_id"], "title": doc["title"], "error": info, "pdf_url": doc["pdf_url"]})
                print(f"{tag} FAIL {doc['blob_id']}: {info}", file=sys.stderr)
            elif status in ("ok",):
                print(f"{tag} ok   {doc['blob_id']} ({info} chars) {doc['title'][:55]}")
            elif status == "cached" and i % 25 == 0:
                print(f"{tag} ...cached through {doc['blob_id']}")

    with open(FAILURES, "w", encoding="utf-8") as f:
        json.dump(failures, f, ensure_ascii=False, indent=2)
    print(f"\ndone: {results} | failures written to {os.path.relpath(FAILURES)}")


if __name__ == "__main__":
    main()
