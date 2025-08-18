# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-08-18
### Added
- **Desktop GUI** for analyzing and merging Liberty (`.lib`) files.
- **Analyze** dialog with:
  - Files tab: size/lines/cell-count, timing/power group counts, detected unit keys.
  - Cells tab: file, cell, base, postfix, pin count, attribute count, timing/power flags; JSON/CSV export.
- **Merge engine**:
  - Merges multiple files **or** multiple variants within a single file (e.g., `FOO1a`, `FOO1b` → `FOO1`).
  - Unions pins; attribute precedence (`earlier`/`later`) via config.
  - Rewrites attribute values that exactly match postfixed cell names to the base name.
  - Preserves inner cell bodies to retain timing/power groups in output.
- **Serializer** to emit valid Liberty syntax, including preserved timing/power sections.
- **Configuration** via `config.yaml` (postfix regex, precedence, rewrite policy).
- **Documentation**:
  - `README.md` (GUI-focused).
  - LaTeX manual in `doc/manual.tex` with a step-by-step GUI tutorial (screenshots 1–8).
  - Built PDF in `doc/main.pdf`.

### Changed
- Parser stores **inner** cell bodies only (no `cell(...) {` header or final `}`) for safe merge splicing.

### Fixed
- Avoids nested `cell(` blocks in merged output.
- Keeps brace balance in merged cell bodies.

### Known Limitations
- **CLI** commands exist but are **not** supported for public use yet (WIP).
- Very large `.lib` files: prefer “Analyze” first, then merge.

[0.1.0]: https://github.com/xiayu87/mrglib/releases/tag/v0.1.0