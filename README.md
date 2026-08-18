# Liberty Merger (GUI)

**Purpose:** Analyze and merge Liberty (`.lib`) files generated using partitioned characterization technique for QDI logic cells.  

**Status:** GUI is the supported path. 
**CLI is in progress.**

---

## Features
- Parse and analyze `.lib` files (cells, pins, timing/power presence).
- Merge multiple files **or** variants within a single file (e.g., `ACELL1a`, `ACELL1b` → `ACELL1`).
- Preserve inner cell bodies (timing/power groups).
- Export merged output to `merged.lib`.
- Simple JSON/CSV export from the analysis dialog.

---

> Tested on Python **3.11+** (works on 3.13). Requires a virtualenv.

---

## Installation

```bash
git clone https://www.github.com/xiayu87/mrglib
cd mrglib
python -m venv .venv
pip install -r requirements.txt
```

---


## Run GUI

```bash
source .venv/bin/activate
python gui_app.py
```

---


## Interface

<p align="center">
  <img src="./doc/5.png" alt="Liberty Merger GUI">
</p>

---

## Citing this work

If you use **mrglib** (or results produced with it) in academic work, please cite the
partition-based Liberty method:

> S. Haider, R. Ding, N. R. Rizvi, and S. Chen,
> “Automated Partition-Based Liberty Modelling for Asynchronous Circuits,”
> *Electronics Letters*, vol. 62, no. 1, Art. no. e70519, 2026.
> [https://doi.org/10.1049/ell2.70519](https://doi.org/10.1049/ell2.70519)

This repository implements **structural merge only** (postfix strip, pin/arc union,
precedence). Characterization and delay arithmetic are outside this tool.

Optional software citation:

> S. Haider, “mrglib: Partition-based Liberty Merging Tool,” Zenodo, 2025.
> [https://doi.org/10.5281/zenodo.17766121](https://doi.org/10.5281/zenodo.17766121)

```bibtex
@article{haider2026partition_letters,
  author  = {Haider, Shahzad and Ding, Ruochen and Rizvi, Naheel Raza and Chen, Song},
  title   = {Automated Partition-Based Liberty Modelling for Asynchronous Circuits},
  journal = {Electronics Letters},
  volume  = {62},
  number  = {1},
  pages   = {e70519},
  year    = {2026},
  doi     = {10.1049/ell2.70519},
  url     = {https://doi.org/10.1049/ell2.70519}
}

@software{haider_mrglib_software,
  author  = {Haider, Shahzad},
  title   = {{mrglib}: Partition-based Liberty Merging Tool},
  year    = {2025},
  doi     = {10.5281/zenodo.17766121},
  url     = {https://github.com/xiayu87/mrglib}
}
