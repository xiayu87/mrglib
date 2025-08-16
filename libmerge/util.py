import re
from dataclasses import dataclass

@dataclass(frozen=True)
class PostfixRule:
    regex: re.Pattern  # compiled with named group 'base' and 'tag'

def make_default_rule():
    # base + underscore + single a-z OR digits, at end
    # Examples: NAND2_a, INV_1, MUX2_b
    return PostfixRule(
        regex=re.compile(r"^(?P<base>.+)_(?P<tag>[a-z0-9])$", re.IGNORECASE)
    )

def strip_postfix(name: str, rule: PostfixRule):
    m = rule.regex.match(name)
    if m:
        return m.group("base"), m.group("tag")
    return name, None
