#!/usr/bin/env python3
"""
convert.py: unified document-to-markdown converter for the zk/ vault.

Dispatches by file type:
    PDF  -> pymupdf4llm  (layout-aware, handles two-column)
    else -> markitdown   (DOCX, PPTX, XLSX, HTML, EPub, CSV, JSON, etc.)

Usage:
    scripts/convert.py <file>                   # print markdown to stdout
    scripts/convert.py <file> -o <output.md>    # write to file
    scripts/convert.py <dir> --batch            # convert all supported files
    scripts/convert.py --formats                # list supported formats

Requires: pymupdf4llm, markitdown (in pyproject.toml).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PDF_SUFFIXES = {".pdf"}

MARKITDOWN_SUFFIXES = {
    ".docx", ".pptx", ".xlsx", ".xls",
    ".html", ".htm",
    ".csv", ".json", ".xml",
    ".epub",
    ".msg",
    ".wav", ".mp3",
}

ALL_SUPPORTED = PDF_SUFFIXES | MARKITDOWN_SUFFIXES


def convert_pdf(path: Path) -> str:
    """Convert PDF to markdown using pymupdf4llm."""
    import pymupdf4llm
    return pymupdf4llm.to_markdown(str(path))


def convert_other(path: Path) -> str:
    """Convert non-PDF formats using markitdown."""
    from markitdown import MarkItDown
    md = MarkItDown(enable_plugins=False)
    result = md.convert(str(path))
    return result.text_content


def convert(path: Path) -> str:
    """Convert a file to markdown, dispatching by suffix."""
    suffix = path.suffix.lower()
    if suffix in PDF_SUFFIXES:
        return convert_pdf(path)
    elif suffix in MARKITDOWN_SUFFIXES:
        return convert_other(path)
    else:
        raise ValueError(
            f"Unsupported format: {suffix}\n"
            f"Supported: {', '.join(sorted(ALL_SUPPORTED))}"
        )


def batch_convert(directory: Path, output_dir: Path | None = None) -> list[tuple[str, float, int]]:
    """Convert all supported files in a directory. Returns list of (filename, seconds, chars)."""
    results = []
    files = sorted(f for f in directory.iterdir() if f.suffix.lower() in ALL_SUPPORTED)

    if not files:
        print(f"No supported files found in {directory}", file=sys.stderr)
        return results

    dest = output_dir or directory
    dest.mkdir(parents=True, exist_ok=True)

    for f in files:
        out_path = dest / f"{f.stem}.md"
        if out_path.exists():
            print(f"  skip (exists): {f.name}", file=sys.stderr)
            continue

        start = time.time()
        try:
            text = convert(f)
            out_path.write_text(text, encoding="utf-8")
            elapsed = time.time() - start
            results.append((f.name, elapsed, len(text)))
            print(f"  {f.name} -> {out_path.name}  ({elapsed:.1f}s, {len(text):,} chars)", file=sys.stderr)
        except Exception as e:
            elapsed = time.time() - start
            print(f"  FAIL {f.name}: {e}  ({elapsed:.1f}s)", file=sys.stderr)
            results.append((f.name, elapsed, -1))

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Convert documents to Markdown for LLM consumption.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", nargs="?", help="File or directory to convert")
    parser.add_argument("-o", "--output", help="Output file path (default: stdout)")
    parser.add_argument("--batch", action="store_true", help="Batch-convert all files in directory")
    parser.add_argument("--output-dir", help="Output directory for batch mode (default: same as input)")
    parser.add_argument("--formats", action="store_true", help="List supported formats and exit")

    args = parser.parse_args()

    if args.formats:
        print("PDF (pymupdf4llm):", ", ".join(sorted(PDF_SUFFIXES)))
        print("Other (markitdown):", ", ".join(sorted(MARKITDOWN_SUFFIXES)))
        return

    if not args.path:
        parser.print_help()
        sys.exit(1)

    path = Path(args.path)

    if args.batch:
        if not path.is_dir():
            print(f"Error: {path} is not a directory", file=sys.stderr)
            sys.exit(1)
        out_dir = Path(args.output_dir) if args.output_dir else None
        results = batch_convert(path, out_dir)
        ok = sum(1 for _, _, c in results if c >= 0)
        fail = sum(1 for _, _, c in results if c < 0)
        total_time = sum(t for _, t, _ in results)
        print(f"\nDone: {ok} converted, {fail} failed, {total_time:.1f}s total", file=sys.stderr)
        return

    if not path.is_file():
        print(f"Error: {path} does not exist or is not a file", file=sys.stderr)
        sys.exit(1)

    text = convert(path)

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Written to {args.output} ({len(text):,} chars)", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
