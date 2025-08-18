from __future__ import annotations
import argparse
from pathlib import Path

from .config import load_config
from .parser import parse_lib
from .merger import merge_libraries
from .serializer import serialize

def main(argv=None):
    p = argparse.ArgumentParser(description="Merge Liberty .lib files.")
    p.add_argument("inputs", nargs="+", help="Input .lib files (one or more).")
    p.add_argument("-o", "--output", required=True, help="Output .lib path.")
    p.add_argument("-c", "--config", help="Optional config.yaml.")
    p.add_argument("--precedence", choices=["earlier","later"], help="Override precedence.")
    args = p.parse_args(argv)

    input_paths = [Path(x) for x in args.inputs]
    if not input_paths:
        p.error("Add at least one input .lib file.")

    cfg, rule = load_config(args.config)
    if args.precedence:
        cfg["precedence"] = args.precedence

    libs = []
    for idx, ip in enumerate(input_paths):
        text = ip.read_text(encoding="utf-8", errors="ignore")
        # keep inner bodies so timing/power survive
        libs.append(parse_lib(text, file_index=idx, keep_raw=True))

    merged = merge_libraries(libs, rule, precedence=cfg["precedence"], preserve_raw=True)
    Path(args.output).write_text(serialize(merged), encoding="utf-8")

if __name__ == "__main__":
    main()