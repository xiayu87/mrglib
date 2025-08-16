import yaml
from pathlib import Path
from .util import make_default_rule, PostfixRule
import re

DEFAULT = {
    "postfix": {
        # Must provide named groups base/tag if you override
        "regex": r"^(?P<base>.+)_(?P<tag>[a-z0-9])$",
        "case_sensitive": False
    },
    "precedence": "later",  # later file wins on attribute collision
    "units_policy": "first", # inherit library-level units from first file
    "rewrite_attr_equals_cellname": True
}

LIB_UNIT_KEYS = {
    "time_unit", "voltage_unit", "current_unit", "leakage_power_unit",
    "pulling_resistance_unit", "capacitive_load_unit", "nom_process",
    "nom_temperature", "nom_voltage"
}

def load_config(p: str | None) -> tuple[dict, PostfixRule]:
    cfg = DEFAULT.copy()
    if p:
        data = yaml.safe_load(Path(p).read_text())
        if data:
            # shallow merge is fine for now
            cfg.update(data)
            if "postfix" in data:
                cfg["postfix"].update(data["postfix"])
    flags = 0 if cfg["postfix"].get("case_sensitive", False) else re.IGNORECASE
    pat = re.compile(cfg["postfix"]["regex"], flags)
    rule = PostfixRule(regex=pat)
    return cfg, rule
