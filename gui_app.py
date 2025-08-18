from __future__ import annotations
import sys
import json
import csv
import traceback
from pathlib import Path

from PyQt6 import QtCore, QtWidgets

# Backend
from libmerge.config import load_config
from libmerge.parser import parse_lib
from libmerge.merger import merge_libraries
from libmerge.serializer import serialize
from libmerge.analyze import analyze_files


# -------------------- Workers --------------------

class MergeWorker(QtCore.QThread):
    progress = QtCore.pyqtSignal(str)
    done = QtCore.pyqtSignal(str)          # output path
    failed = QtCore.pyqtSignal(str)        # error message

    def __init__(self, inputs: list[Path], out_path: Path, config_path: Path | None, precedence: str | None):
        super().__init__()
        self.inputs = inputs
        self.out_path = out_path
        self.config_path = config_path
        self.precedence = precedence

    def run(self):
        try:
            self.progress.emit("Loading config…")
            cfg, rule = load_config(str(self.config_path) if self.config_path else None)
            if self.precedence:
                cfg["precedence"] = self.precedence

            self.progress.emit(f"Parsing {len(self.inputs)} file(s)…")
            libs = []
            for idx, p in enumerate(self.inputs):
                self.progress.emit(f"Parsing: {p.name}")
                text = p.read_text(encoding="utf-8", errors="ignore")
                # IMPORTANT: keep_raw=True so timing/power inner bodies are retained
                libs.append(parse_lib(text, file_index=idx, keep_raw=True))

            self.progress.emit("Merging…")
            # IMPORTANT: preserve_raw=True so inner bodies are spliced into merged cells
            merged = merge_libraries(libs, rule, precedence=cfg["precedence"], preserve_raw=True)

            self.progress.emit("Serializing…")
            out_text = serialize(merged)
            self.out_path.write_text(out_text, encoding="utf-8")

            self.done.emit(str(self.out_path))
        except Exception as e:
            tb = traceback.format_exc()
            self.failed.emit(f"{e}\n\n{tb}")


class AnalyzeWorker(QtCore.QThread):
    progress = QtCore.pyqtSignal(str)
    done = QtCore.pyqtSignal(dict)         # report dict
    failed = QtCore.pyqtSignal(str)

    def __init__(self, inputs: list[Path], config_path: Path | None):
        super().__init__()
        self.inputs = inputs
        self.config_path = config_path

    def run(self):
        try:
            self.progress.emit("Loading config…")
            _cfg, rule = load_config(str(self.config_path) if self.config_path else None)
            self.progress.emit(f"Analyzing {len(self.inputs)} file(s)…")
            report = analyze_files([str(p) for p in self.inputs], rule)
            self.done.emit(report)
        except Exception as e:
            tb = traceback.format_exc()
            self.failed.emit(f"{e}\n\n{tb}")


# -------------------- UI: Summary Dialog --------------------

class SummaryDialog(QtWidgets.QDialog):
    def __init__(self, report: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lib Analysis Summary")
        self.resize(960, 620)

        tabs = QtWidgets.QTabWidget()

        # Files tab (text summary)
        text = QtWidgets.QPlainTextEdit()
        text.setReadOnly(True)
        lines = []
        for f in report.get("files", []):
            lines.append(f"File: {f.get('file','')}")
            lines.append(f"  size: {f.get('size_bytes',0)} bytes, lines: {f.get('lines',0)}, cells: {f.get('cells',0)}")
            lines.append(
                "  timing groups: {tg}, internal_power: {ip}, leakage_power: {lp}".format(
                    tg=f.get("timing_groups", 0),
                    ip=f.get("internal_power_groups", 0),
                    lp=f.get("leakage_power_groups", 0),
                )
            )
            units = f.get("units_present", [])
            if units:
                lines.append("  units: " + ", ".join(units))
            incs = f.get("includes", [])
            if incs:
                lines.append(f"  includes: {len(incs)}")
            kind = f.get("lib_kind")
            if kind:
                lines.append(f"  detected type: {kind}")
            lines.append("")
        s = report.get("summary", {})
        lines.append(
            f"TOTAL files: {s.get('files',0)} | cells listed: {s.get('cells_total',0)} | unique bases: {s.get('unique_bases',0)}"
        )
        lines.append(
            f"cells with timing: {s.get('cells_with_timing',0)} | cells with power: {s.get('cells_with_power',0)}"
        )
        text.setPlainText("\n".join(lines))
        tabs.addTab(text, "Files")

        # Cells tab (table)
        table = QtWidgets.QTableWidget()
        rows = report.get("cells", [])
        cap = min(len(rows), 5000)  # guard for very large inputs
        cols = ["file", "cell", "base", "postfix", "pins", "attrs_count", "has_timing", "has_power"]
        table.setRowCount(cap)
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        for i in range(cap):
            r = rows[i]
            for j, k in enumerate(cols):
                item = QtWidgets.QTableWidgetItem(str(r.get(k, "")))
                if k in ("pins", "attrs_count"):
                    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
                table.setItem(i, j, item)
        table.setSortingEnabled(True)
        table.resizeColumnsToContents()
        tabs.addTab(table, f"Cells ({cap}{' of '+str(len(rows)) if len(rows)>cap else ''})")

        # Buttons
        btn_json = QtWidgets.QPushButton("Export JSON…")
        btn_csv = QtWidgets.QPushButton("Export CSV…")
        btn_close = QtWidgets.QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_json.clicked.connect(lambda: self._save_json(report))
        btn_csv.clicked.connect(lambda: self._save_csv(rows))

        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(btn_json)
        btns.addWidget(btn_csv)
        btns.addWidget(btn_close)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(tabs, 1)
        lay.addLayout(btns)

    def _save_json(self, report: dict):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save report.json", "report.json", "JSON (*.json);;All (*)")
        if path:
            Path(path).write_text(json.dumps(report, indent=2), encoding="utf-8")

    def _save_csv(self, rows: list[dict]):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save cells.csv", "cells.csv", "CSV (*.csv);;All (*)")
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(
                    f, fieldnames=["file", "cell", "base", "postfix", "pins", "attrs_count", "has_timing", "has_power"]
                )
                w.writeheader()
                w.writerows(rows)


# -------------------- Main Window --------------------

class MainWin(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Liberty Merger (desktop)")
        self.resize(860, 580)

        # Inputs list
        self.list_files = QtWidgets.QListWidget()
        self.list_files.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)

        btn_add = QtWidgets.QPushButton("Add .lib files…")
        btn_add.clicked.connect(self.add_files)
        btn_remove = QtWidgets.QPushButton("Remove selected")
        btn_remove.clicked.connect(self.remove_selected)
        btn_clear = QtWidgets.QPushButton("Clear")
        btn_clear.clicked.connect(self.list_files.clear)

        # Config
        self.edit_config = QtWidgets.QLineEdit()
        self.edit_config.setPlaceholderText("Optional: config.yaml")
        btn_cfg = QtWidgets.QPushButton("Browse…")
        btn_cfg.clicked.connect(self.pick_config)

        # Output
        self.edit_out = QtWidgets.QLineEdit()
        self.edit_out.setPlaceholderText("Output .lib path (e.g., merged.lib)")
        btn_out = QtWidgets.QPushButton("Browse…")
        btn_out.clicked.connect(self.pick_output)

        # Precedence
        self.combo_prec = QtWidgets.QComboBox()
        self.combo_prec.addItems(["default (from config)", "earlier", "later"])

        # Actions
        self.btn_analyze = QtWidgets.QPushButton("Analyze")
        self.btn_analyze.clicked.connect(self.run_analyze)

        self.btn_run = QtWidgets.QPushButton("Merge")
        self.btn_run.clicked.connect(self.run_merge)

        # Log
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)

        # Layouts
        left = QtWidgets.QVBoxLayout()
        left.addWidget(QtWidgets.QLabel("Input .lib files"))
        left.addWidget(self.list_files, 1)
        row_btns = QtWidgets.QHBoxLayout()
        row_btns.addWidget(btn_add)
        row_btns.addWidget(btn_remove)
        row_btns.addWidget(btn_clear)
        left.addLayout(row_btns)

        form = QtWidgets.QFormLayout()
        cfg_row = QtWidgets.QHBoxLayout()
        cfg_row.addWidget(self.edit_config, 1); cfg_row.addWidget(btn_cfg)
        form.addRow("Config:", cfg_row)
        out_row = QtWidgets.QHBoxLayout()
        out_row.addWidget(self.edit_out, 1); out_row.addWidget(btn_out)
        form.addRow("Output:", out_row)
        form.addRow("Precedence:", self.combo_prec)

        top = QtWidgets.QHBoxLayout()
        top.addLayout(left, 3)
        right = QtWidgets.QVBoxLayout()
        right.addLayout(form)
        action_row = QtWidgets.QHBoxLayout()
        action_row.addWidget(self.btn_analyze)
        action_row.addWidget(self.btn_run)
        right.addLayout(action_row)
        right.addWidget(QtWidgets.QLabel("Log"))
        right.addWidget(self.log, 1)
        top.addLayout(right, 5)

        self.setLayout(top)
        self.worker: MergeWorker | None = None
        self.workerA: AnalyzeWorker | None = None

    # ---- UI helpers ----

    def add_files(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Select Liberty files", "", "Liberty (*.lib);;All (*)")
        for f in files:
            self.list_files.addItem(f)

    def remove_selected(self):
        for item in self.list_files.selectedItems():
            self.list_files.takeItem(self.list_files.row(item))

    def pick_config(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select config.yaml", "", "YAML (*.yaml *.yml);;All (*)")
        if path:
            self.edit_config.setText(path)

    def pick_output(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Select output .lib", "merged.lib", "Liberty (*.lib);;All (*)")
        if path:
            self.edit_out.setText(path)

    # ---- Merge ----

    def run_merge(self):
        inputs = [Path(self.list_files.item(i).text()) for i in range(self.list_files.count())]
        if len(inputs) < 1:
            self.log.appendPlainText("Add at least one .lib file.")
            return
        out_path = Path(self.edit_out.text().strip() or "merged.lib")
        cfg_path = Path(self.edit_config.text().strip()) if self.edit_config.text().strip() else None

        prec_sel = self.combo_prec.currentText()
        precedence = None
        if "earlier" in prec_sel:
            precedence = "earlier"
        elif "later" in prec_sel:
            precedence = "later"

        self.btn_run.setEnabled(False)
        self.btn_analyze.setEnabled(False)
        self.log.appendPlainText(f"Starting merge → {out_path}")
        self.worker = MergeWorker(inputs, out_path, cfg_path, precedence)
        self.worker.progress.connect(self.log.appendPlainText)
        self.worker.done.connect(self.on_done_merge)
        self.worker.failed.connect(self.on_failed_merge)
        self.worker.start()

    def on_done_merge(self, out_path: str):
        self.log.appendPlainText(f"Done: {out_path}")
        QtWidgets.QMessageBox.information(self, "Merge complete", f"Merged file written:\n{out_path}")
        self.btn_run.setEnabled(True)
        self.btn_analyze.setEnabled(True)
        self.worker = None

    def on_failed_merge(self, msg: str):
        self.log.appendPlainText("ERROR:\n" + msg)
        QtWidgets.QMessageBox.critical(self, "Error", msg)
        self.btn_run.setEnabled(True)
        self.btn_analyze.setEnabled(True)
        self.worker = None

    # ---- Analyze ----

    def run_analyze(self):
        items = self.list_files.selectedItems()
        if items:
            inputs = [Path(it.text()) for it in items]
        else:
            inputs = [Path(self.list_files.item(i).text()) for i in range(self.list_files.count())]
        if not inputs:
            self.log.appendPlainText("Add at least one .lib file to analyze.")
            return

        cfg_path = Path(self.edit_config.text().strip()) if self.edit_config.text().strip() else None
        self.btn_run.setEnabled(False)
        self.btn_analyze.setEnabled(False)
        self.log.appendPlainText(f"Analyzing {len(inputs)} file(s)…")
        self.workerA = AnalyzeWorker(inputs, cfg_path)
        self.workerA.progress.connect(self.log.appendPlainText)
        self.workerA.done.connect(self.on_done_analyze)
        self.workerA.failed.connect(self.on_failed_analyze)
        self.workerA.start()

    def on_done_analyze(self, report: dict):
        self.log.appendPlainText("Analysis complete.")
        dlg = SummaryDialog(report, self)
        dlg.exec()
        self.btn_run.setEnabled(True)
        self.btn_analyze.setEnabled(True)
        self.workerA = None

    def on_failed_analyze(self, msg: str):
        self.log.appendPlainText("ANALYZE ERROR:\n" + msg)
        QtWidgets.QMessageBox.critical(self, "Analyze error", msg)
        self.btn_run.setEnabled(True)
        self.btn_analyze.setEnabled(True)
        self.workerA = None


# -------------------- App entry --------------------

def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWin()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()