import sys, argparse
from pathlib import Path
from .config import load_config
from .parser import parse_lib
from .merger import merge_libraries
from .serializer import serialize

def main(argv=None):
    p = argparse.ArgumentParser(prog="libmerge",
        description="Merge multiple Liberty .lib files; strip postfix (e.g., _a/_b) and unify cells.")
    p.add_argument("-o", "--out", required=True, help="Output .lib path")
    p.add_argument("-c", "--config", help="YAML config (postfix regex, policies)")
    p.add_argument("--precedence", choices=["earlier","later"], help="Attr collision policy (default from config)")
    p.add_argument("inputs", nargs="+", help="Input .lib files (2+)")
    args = p.parse_args(argv)

    if len(args.inputs) < 2:
        p.error("Need at least two input .lib files")

    cfg, rule = load_config(args.config)
    if args.precedence:
        cfg["precedence"] = args.precedence

    libs = []
    for idx, path in enumerate(args.inputs):
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        libs.append(parse_lib(text, file_index=idx))

    merged = merge_libraries(libs, rule, precedence=cfg["precedence"])
    out_text = serialize(merged)
    Path(args.out).write_text(out_text, encoding="utf-8")
    print(f"[libmerge] merged {len(args.inputs)} files → {args.out}")

if __name__ == "__main__":
    main()
