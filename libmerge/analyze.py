from __future__ import annotations
import json, re
from dataclasses import asdict
from pathlib import Path
from typing import Optional, Pattern
from .config import load_config
from .parser import parse_lib, Cell
from .util import strip_postfix, PostfixRule

def analyze_files(
    paths: list[str | Path],
    rule: PostfixRule,
    only_pat: Optional[Pattern[str]] = None,
    limit_cells: Optional[int] = None,
) -> dict:
    files_summary = []
    cells_rows = []
    uniq_bases = set()
    cells_with_timing = 0
    cells_with_power = 0

    processed = 0
    for fi, p in enumerate(paths):
        p = Path(p)
        text = p.read_text(encoding="utf-8", errors="ignore")
        # keep_raw=False keeps memory low but still marks has_timing/has_power
        lib = parse_lib(text, file_index=fi, keep_raw=False)

        # file-level skim
        size = p.stat().st_size
        lines = text.count("\n") + 1
        includes = []
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("include(") or s.startswith('include ('):
                includes.append(s)

        # group counters (cheap regexes)
        timing_groups = len(re.findall(r'^\s*timing\s*(\(|\{)', text, flags=re.M))
        internal_power = len(re.findall(r'^\s*internal_power\s*(\(|\{)', text, flags=re.M))
        leakage_power = len(re.findall(r'^\s*leakage_power\s*(\(|\{)', text, flags=re.M))

        files_summary.append({
            "file": str(p),
            "size_bytes": size,
            "lines": lines,
            "cells": len(lib.cells),
            "timing_groups": timing_groups,
            "internal_power_groups": internal_power,
            "leakage_power_groups": leakage_power,
            "includes": includes,
            "units_present": sorted([k for k in lib.attrs.keys() if k.endswith("_unit")])
        })

        for name, cell in lib.cells.items():
            base, tag = strip_postfix(name, rule)
            if only_pat and not only_pat.search(base):
                continue
            if limit_cells is not None and processed >= limit_cells:
                break
            processed += 1
            row = {
                "file": p.name,
                "cell": name,
                "base": base,
                "postfix": tag,
                "pins": len(cell.pins),
                "attrs_count": len(cell.attrs),
                "has_timing": cell.has_timing,
                "has_power": cell.has_power,
            }
            cells_rows.append(row)
            uniq_bases.add(base)
            if cell.has_timing: cells_with_timing += 1
            if cell.has_power:  cells_with_power += 1

    report = {
        "files": files_summary,
        "cells": cells_rows,
        "summary": {
            "files": len(paths),
            "cells_total": len(cells_rows),
            "unique_bases": len(uniq_bases),
            "cells_with_timing": cells_with_timing,
            "cells_with_power": cells_with_power,
        }
    }
    return report
