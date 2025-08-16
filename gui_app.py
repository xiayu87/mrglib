from __future__ import annotations
import sys, traceback
from pathlib import Path

from PyQt6 import QtCore, QtWidgets
# Your backend:
from libmerge.config import load_config
from libmerge.parser import parse_lib
from libmerge.merger import merge_libraries
from libmerge.serializer import serialize

class MergeWorker(QtCore.QThread):
    progress = QtCore.pyqtSignal(str)
    done = QtCore.pyqtSignal(str)          # output path
    failed = QtCore.pyqtSignal(str)        # error message

    def __init__(self, inputs: list[Path], out_path: Path, config_path: Path|None, precedence: str|None):
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
                libs.append(parse_lib(text, file_index=idx))

            self.progress.emit("Merging…")
            merged = merge_libraries(libs, rule, precedence=cfg["precedence"])

            self.progress.emit("Serializing…")
            out_text = serialize(merged)
            self.out_path.write_text(out_text, encoding="utf-8")

            self.done.emit(str(self.out_path))
        except Exception as e:
            tb = traceback.format_exc()
            self.failed.emit(f"{e}\n\n{tb}")

class MainWin(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Liberty Merger (desktop)")
        self.resize(760, 520)

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

        # Run
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
        right.addWidget(self.btn_run)
        right.addWidget(QtWidgets.QLabel("Log"))
        right.addWidget(self.log, 1)
        top.addLayout(right, 5)

        self.setLayout(top)
        self.worker: MergeWorker|None = None

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

    def run_merge(self):
        inputs = [Path(self.list_files.item(i).text()) for i in range(self.list_files.count())]
        if len(inputs) < 2:
            self.log.appendPlainText("Need at least two input files.")
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
        self.log.appendPlainText(f"Starting merge → {out_path}")
        self.worker = MergeWorker(inputs, out_path, cfg_path, precedence)
        self.worker.progress.connect(self.log.appendPlainText)
        self.worker.done.connect(self.on_done)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def on_done(self, out_path: str):
        self.log.appendPlainText(f"Done: {out_path}")
        QtWidgets.QMessageBox.information(self, "Merge complete", f"Merged file written:\n{out_path}")
        self.btn_run.setEnabled(True)
        self.worker = None

    def on_failed(self, msg: str):
        self.log.appendPlainText("ERROR:\n" + msg)
        QtWidgets.QMessageBox.critical(self, "Error", msg)
        self.btn_run.setEnabled(True)
        self.worker = None

def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWin()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
