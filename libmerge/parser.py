from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# Very tolerant, line-oriented parser:
# - Captures libraries -> cells
# - For cells: collects 'pin <NAME>;' and 'attribute <key> = <val>;'
# - Any other nested content under a cell is preserved as raw text (verbatim) in 'body'
#
# This keeps timing/power groups intact without understanding them yet.

@dataclass
class Cell:
    name: str
    pins: Dict[str, None] = field(default_factory=dict)
    attrs: Dict[str, str] = field(default_factory=dict)
    raw_body: List[str] = field(default_factory=list)  # lines between { ... } excluding parsed pins/attrs
    src_file_index: int = -1

@dataclass
class Library:
    name: str | None
    attrs: Dict[str, str] = field(default_factory=dict)  # library-level attrs
    cells: Dict[str, Cell] = field(default_factory=dict)

def _strip_comment(line: str) -> str:
    # naive // and /* */ handling on single line
    if "/*" in line and "*/" in line:
        # drop comment content
        s = line
        while "/*" in s and "*/" in s:
            a = s.find("/*")
            b = s.find("*/", a + 2)
            if b == -1: break
            s = s[:a] + s[b+2:]
        line = s
    if "//" in line:
        return line.split("//", 1)[0]
    return line

def parse_lib(text: str, file_index: int) -> Library:
    lines = text.splitlines()
    i, n = 0, len(lines)
    lib = Library(name=None)
    current_cell: Cell | None = None
    depth = 0

    while i < n:
        raw = lines[i]
        s = _strip_comment(raw).strip()
        i += 1
        if not s:
            if current_cell: current_cell.raw_body.append(raw)
            continue

        # library name (optional)
        if lib.name is None and s.startswith("library"):
            # library (<name>) {  OR  library (<"name">) {
            lib.name = s
            depth = 1
            continue

        if s.startswith("cell "):
            # start cell
            # expect: cell NAME {   or cell(NAME) {
            name_part = s[len("cell "):].strip()
            # normalize common form "cell NAME {"
            name = name_part.split("{",1)[0].strip()
            name = name.replace("(", " ").replace(")", " ").strip()
            current_cell = Cell(name=name, src_file_index=file_index)
            lib.cells[name] = current_cell
            depth = 1
            continue

        if current_cell:
            # detect end of cell
            if s == "}":
                current_cell = None
                depth = 0
                continue

            # pin line
            if s.startswith("pin "):
                # pin NAME; or pin(NAME) { ... }   -> we only capture simple NAME;
                if s.endswith(";"):
                    pname = s[len("pin "):].rstrip(";").strip()
                    pname = pname.replace("(", " ").replace(")", " ").strip()
                    if pname:
                        current_cell.pins[pname] = None
                        continue
                # otherwise keep raw
                current_cell.raw_body.append(raw)
                continue

            # attribute line: attribute key = value;
            if s.startswith("attribute "):
                if "=" in s and s.endswith(";"):
                    left, right = s.split("=", 1)
                    key = left.replace("attribute", "").strip()
                    val = right.rstrip(";").strip()
                    # strip quotes if quoted
                    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    if key:
                        current_cell.attrs[key] = val
                        continue
                current_cell.raw_body.append(raw)
                continue

            # any other line inside a cell
            current_cell.raw_body.append(raw)
            continue

        # library-level attributes (very simple "key : value ;" pattern)
        if ":" in s and s.endswith(";") and "{" not in s:
            key, val = s.split(":", 1)
            key = key.strip()
            val = val.rstrip(";").strip()
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if key:
                lib.attrs[key] = val
                continue

        # default: ignore or capture? We ignore top-level non-matched lines for now.

    return lib
