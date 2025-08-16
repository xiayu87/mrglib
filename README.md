# libmerge (CLI)

Merge multiple Liberty `.lib` files where cells are suffixed (e.g., `NAND2_a`, `NAND2_b`).
Strips postfix and merges by base name.

- Pins: union
- Attributes: later file wins (configurable)
- Library unit attrs: inherited from first file
- Rewrites attribute values that exactly match a postfixed cell name

## Install & run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pyyaml
python -m libmerge.cli -o merged.lib a.lib b.lib
