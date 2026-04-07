# Local Papers

Research papers stored as local PDFs in `zk/papers/` (L3 externally certified knowledge: peer-reviewed or high-citation). Used for deep reading sessions when a paper is not available via URL or when the workflow needs the canonical PDF on disk.

## Directory Structure

```
zk/papers/
├── <slug>.pdf            ← raw PDF
├── <slug>-notes.md       ← optional notes/artifacts
└── ...
```

## How to Use

Papers are referenced by filename. The Reader agent reads PDFs directly via the Read tool. Use a stable, descriptive slug (kebab-case title or `<venue>-<id>`) as the basename.

### Naming convention
`<slugified-title>.pdf` for standalone papers, or `<source>-<id>.pdf` when the paper has a stable external identifier.

## No CLI

This is a local source — no CLI or API. The agent reads PDFs directly from the filesystem.
