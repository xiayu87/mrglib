from typing import Dict
import re

from .parser import Library, Cell
from .util import strip_postfix, PostfixRule
from .config import LIB_UNIT_KEYS

def _normalize_lib_name(lib_name_line: str | None, rule: PostfixRule) -> str | None:
    if not lib_name_line:
        return None
    m = re.match(r'^\s*library\s*\(\s*("?)([^")\s]+)\1\s*\)\s*\{\s*$', lib_name_line)
    if not m:
        return lib_name_line
    q, name = m.group(1), m.group(2)
    base, tag = strip_postfix(name, rule)
    if tag is None:
        return lib_name_line
    quoted = f"{q}{base}{q}"
    return f"library ({quoted}) {{"

def merge_libraries(
    libs: list[Library],
    rule: PostfixRule,
    precedence: str = "later",
    preserve_raw: bool = True,   # keep inner timing/power bodies
) -> Library:
    merged = Library(name=libs[0].name, attrs=dict(libs[0].attrs), cells={})
    merged.name = _normalize_lib_name(merged.name, rule) or merged.name

    # adopt missing unit attrs from later libs (first lib wins otherwise)
    for lib in libs[1:]:
        for k in LIB_UNIT_KEYS:
            if k in lib.attrs and k not in merged.attrs:
                merged.attrs[k] = lib.attrs[k]

    postfixed_to_base: Dict[str, str] = {}
    base_cells: Dict[str, Cell] = {}

    def merge_cell_into(base_name: str, src: Cell):
        if base_name not in base_cells:
            base_cells[base_name] = Cell(name=base_name, src_file_index=src.src_file_index)
        dst = base_cells[base_name]

        # pins: union
        for p in src.pins.keys():
            dst.pins[p] = None

        # attrs: precedence policy
        if precedence == "later":
            for k, v in src.attrs.items():
                dst.attrs[k] = v
        else:  # earlier
            for k, v in src.attrs.items():
                if k not in dst.attrs:
                    dst.attrs[k] = v

        # carry inner raw bodies (safe: they no longer contain 'cell { ... }' headers)
        if preserve_raw and src.raw_body:
            dst.raw_body.append(f"/* merged-from-file-{src.src_file_index} */")
            dst.raw_body.extend(src.raw_body)

        # flags OR
        if src.has_timing:
            dst.has_timing = True
        if src.has_power:
            dst.has_power = True

    # merge all cells (single-file or multi-file)
    for lib in libs:
        for cell_name, cell in lib.cells.items():
            base, _tag = strip_postfix(cell_name, rule)
            postfixed_to_base[cell_name] = base
            merge_cell_into(base, cell)

    # rewrite attribute values that equal a postfixed cell name → base
    for c in base_cells.values():
        for k, v in list(c.attrs.items()):
            if v in postfixed_to_base:
                c.attrs[k] = postfixed_to_base[v]

    merged.cells = base_cells
    return merged