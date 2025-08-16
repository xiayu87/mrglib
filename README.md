# mrglib

Tools to **analyze** and **merge** Liberty `.lib` files where cells are suffixed (e.g. `NAND2_a`, `NAND2_b`).  
Merging strips the suffix, unions pins, rewrites attributes that reference postfixed cell names, and respects attribute precedence.

- **Analyze:** quick, read-only summary of files (cells, pins, timing/power presence, units, includes).
- **Merge:** combine 2+ `.lib` into one by base cell name.

> Tested on Python **3.11+** (works on 3.13). Use a virtualenv.

---

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install PyQt6 pyyaml

## Run GUI

source .venv/bin/activate
python gui_app.py