from typing import Dict, Tuple
from .parser import Library, Cell
from .util import strip_postfix, PostfixRule
from .config import LIB_UNIT_KEYS

def merge_libraries(libs: list[Library], rule: PostfixRule, precedence: str = "later") -> Library:
    # Start with first library name/attrs; lock library units to the first
    merged = Library(name=libs[0].name, attrs=dict(libs[0].attrs), cells={})

    # Normalize unit attrs policy: inherit from the first lib only
    for lib in libs[1:]:
        for k in LIB_UNIT_KEYS:
            if k in lib.attrs and k not in merged.attrs:
                # It’s rare but if first didn’t have it, adopt — else ignore
                merged.attrs[k] = lib.attrs[k]

    # Map postfixed->base and collect seen base names
    # Also need a reverse lookup of all postfixed forms to base for rewriting
    postfixed_to_base: Dict[str, str] = {}
    base_cells: Dict[str, Cell] = {}

    def merge_cell_into(base_name: str, src: Cell):
        if base_name not in base_cells:
            base_cells[base_name] = Cell(name=base_name, src_file_index=src.src_file_index)
        dst = base_cells[base_name]
        # Pins: union
        for p in src.pins.keys():
            dst.pins[p] = None
        # Attributes: precedence
        if precedence == "later":
            # copy all, overwrite collisions
            for k, v in src.attrs.items():
                # library-level unit attrs do not belong at cell scope; just overwrite normally
                dst.attrs[k] = v
        else:  # "earlier"
            for k, v in src.attrs.items():
                if k not in dst.attrs:
                    dst.attrs[k] = v
        # Raw body: we preserve source raw blocks by appending with a marker
        # (Future: do a structured merge for timing/power.)
        if src.raw_body:
            dst.raw_body.append(f"/* merged-from-file-{src.src_file_index} */")
            dst.raw_body.extend(src.raw_body)

    # Walk each library in order, strip postfix from cell names, and merge
    for lib in libs:
        for cell_name, cell in lib.cells.items():
            base, tag = strip_postfix(cell_name, rule)
            postfixed_to_base[cell_name] = base
            merge_cell_into(base, cell)

    # Rewrite attribute values that exactly match a *postfixed* cell name -> base name
    for c in base_cells.values():
        for k, v in list(c.attrs.items()):
            if v in postfixed_to_base:
                c.attrs[k] = postfixed_to_base[v]

    merged.cells = base_cells
    return merged
