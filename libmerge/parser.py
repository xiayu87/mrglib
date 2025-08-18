from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Tolerant, line-oriented parser:
# - Captures libraries -> cells
# - For cells: collects pin names + simple attributes
# - Detects timing/power (incl. CCS/ECSM variants)
# - Tracks braces so a cell ends only when its braces close
# - When keep_raw=True, stores ONLY the **inner** cell body
#   (no opening 'cell ... {' line, no final closing '}')

@dataclass
class Cell:
    name: str
    pins: Dict[str, None] = field(default_factory=dict)
    attrs: Dict[str, str] = field(default_factory=dict)
    raw_body: List[str] = field(default_factory=list)   # inner lines of the cell body
    src_file_index: int = -1
    has_timing: bool = False
    has_power: bool = False

@dataclass
class Library:
    name: Optional[str]
    attrs: Dict[str, str] = field(default_factory=dict)
    cells: Dict[str, Cell] = field(default_factory=dict)

def _strip_comment(line: str) -> str:
    """Naive // and /* */ handling on a single line."""
    if "/*" in line and "*/" in line:
        s = line
        while "/*" in s and "*/" in s:
            a = s.find("/*")
            b = s.find("*/", a + 2)
            if b == -1:
                break
            s = s[:a] + s[b + 2:]
        line = s
    if "//" in line:
        return line.split("//", 1)[0]
    return line

def parse_lib(text: str, file_index: int, keep_raw: bool = True) -> Library:
    import re

    lines = text.splitlines()
    i, n = 0, len(lines)
    lib = Library(name=None)
    current_cell: Optional[Cell] = None
    depth = 0  # cell-local brace depth

    while i < n:
        raw = lines[i]
        s = _strip_comment(raw).strip()
        i += 1

        if not s:
            if current_cell and keep_raw:
                current_cell.raw_body.append(raw)
            continue

        # library header (kept verbatim)
        if lib.name is None and s.startswith("library"):
            lib.name = s
            continue

        # ----- start of a cell (support 'cell(NAME){' and 'cell NAME {'); DO NOT match 'cell_leakage_power' -----
        if re.match(r'^\s*cell\s*\(', s) or re.match(r'^\s*cell\s+[A-Za-z0-9_]+\s*\{', s):
            # extract name
            if "(" in s and s.find("(") < s.find("{"):
                name = s[s.find("(") + 1 : s.find(")")].strip()
            else:
                before_brace = s.split("{", 1)[0]
                parts = before_brace.split()
                name = parts[1].strip() if len(parts) > 1 else before_brace.strip()
            name = name.replace("(", " ").replace(")", " ").strip()

            current_cell = Cell(name=name, src_file_index=file_index)
            lib.cells[name] = current_cell

            # initialize depth from this line
            opens = raw.count("{")
            closes = raw.count("}")
            depth = opens - closes
            if depth <= 0:
                depth = 1  # ensure we treat subsequent lines as inside the cell

            # IMPORTANT: do **not** append the opening 'cell ... {' line into raw_body
            continue

        # ----- inside a cell -----
        if current_cell:
            # pins: support pin(NAME){...} and 'pin NAME;'
            if s.startswith("pin"):
                m = re.match(r'^pin\s*\(\s*([^)]+)\s*\)\s*\{', s)
                if m:
                    pname = m.group(1).strip()
                    if pname: current_cell.pins[pname] = None
                elif s.endswith(";"):
                    pname = s[len("pin "):].rstrip(";").strip()
                    pname = pname.replace("(", " ").replace(")", " ").strip()
                    if pname: current_cell.pins[pname] = None

            # timing / power flags (incl. CCS/ECSM)
            if (s.startswith("timing") or s.startswith("ccs_timing") or s.startswith("ecsm_timing")):
                current_cell.has_timing = True
            if (s.startswith("internal_power") or s.startswith("leakage_power") or
                s.startswith("power") or s.startswith("ccs_power") or s.startswith("ecsm_power")):
                current_cell.has_power = True

            # attributes inside cell
            if s.startswith("attribute "):
                if "=" in s and s.endswith(";"):
                    left, right = s.split("=", 1)
                    key = left.replace("attribute", "").strip()
                    val = right.rstrip(";").strip()
                    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    if key:
                        current_cell.attrs[key] = val
            else:
                # generic "key : value ;" (no '{')
                if ":" in s and s.endswith(";") and "{" not in s:
                    k2, v2 = s.split(":", 1)
                    k2 = k2.strip()
                    v2 = v2.rstrip(";").strip()
                    if (v2.startswith('"') and v2.endswith('"')) or (v2.startswith("'") and v2.endswith("'")):
                        v2 = v2[1:-1]
                    if k2:
                        current_cell.attrs[k2] = v2

            # brace accounting and raw capture (skip the final closing line)
            opens = raw.count("{")
            closes = raw.count("}")
            if keep_raw:
                if not (s == "}" and (depth + opens - closes) <= 0):
                    current_cell.raw_body.append(raw)

            depth += opens - closes
            if depth <= 0:
                current_cell = None
                depth = 0
            continue

        # ----- outside a cell: library-level attributes "key : value ;" -----
        if ":" in s and s.endswith(";") and "{" not in s:
            key, val = s.split(":", 1)
            key = key.strip()
            val = val.rstrip(";").strip()
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if key:
                lib.attrs[key] = val
            continue

        # default: ignore unmatched top-level lines

    return lib