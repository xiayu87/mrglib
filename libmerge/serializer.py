from .parser import Library, Cell

def quote_if_needed(s: str) -> str:
    if any(ch.isspace() for ch in s) or s == "" or s.startswith('"') or s.startswith("'"):
        return '"' + s.replace('"', '\\"') + '"'
    return s

def serialize(lib: Library) -> str:
    out = []
    # Library header if we captured one; otherwise just emit attrs + cells
    if lib.name and lib.name.strip().endswith("{"):
        out.append(lib.name)
    # library-level attrs
    for k, v in lib.attrs.items():
        out.append(f"  {k} : {quote_if_needed(str(v))};")
    if lib.name and lib.name.strip().endswith("{"):
        out.append("")  # blank line
    # Cells
    for cname in sorted(lib.cells.keys()):
        cell = lib.cells[cname]
        out.append(f"  cell {cname} {{")
        # pins
        for p in sorted(cell.pins.keys()):
            out.append(f"    pin {p};")
        # attrs
        for k in sorted(cell.attrs.keys()):
            out.append(f"    attribute {k} = {quote_if_needed(str(cell.attrs[k]))};")
        # raw body preserved
        for line in cell.raw_body:
            out.append("    " + line.rstrip())
        out.append("  }")
        out.append("")
    if lib.name and lib.name.strip().endswith("{"):
        out.append("}")
    return "\n".join(out).rstrip() + "\n"
