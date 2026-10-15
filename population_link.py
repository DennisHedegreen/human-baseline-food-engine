"""Local dependency adapter: reuse first-layer code and data, never fork it."""
import importlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
VENDORED = ROOT / "_vendor/population"
SOURCE = VENDORED if VENDORED.is_dir() else ROOT.parent / "human-baseline-population"
if VENDORED.is_dir():
    import hashlib
    import json
    lock = json.loads((ROOT / "dependency-lock.json").read_text())
    for entry in lock["files"]:
        path = ROOT / entry["path"]
        if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise RuntimeError(f"Changed or missing pinned population dependency: {entry['path']}")
sys.path.insert(0, str(SOURCE))
try:
    shared = importlib.import_module("simple_model")
finally:
    sys.path.remove(str(SOURCE))
for module_name in ("simple_model", "scenario_core"):
    if Path(sys.modules[module_name].__file__).resolve().parent != SOURCE:
        raise RuntimeError(f"Wrong shared first-layer dependency: {module_name}")

COUNTRIES = shared.COUNTRIES
load_population = shared.load_population


def build_demand(mode, kcal, codes=None, people=None, name=None, frame=None):
    """Return the original energy-result contract plus descriptive country rows."""
    if mode == "Custom population":
        return shared.energy_result(people, kcal, (name or "Custom population").strip() or "Custom population"), []
    if mode not in ("Country", "Compare countries", "EU27"):
        raise ValueError("Unsupported population mode")
    codes = list(COUNTRIES) if mode == "EU27" else list(codes or [])
    if not codes or len(codes) != len(set(codes)):
        raise ValueError("Choose distinct countries")
    if mode == "Country" and len(codes) != 1:
        raise ValueError("Country mode requires one country")
    frame = load_population() if frame is None else frame
    rows = [shared.demographics(frame, code) for code in codes]
    total = sum(row["people"] for row in rows)
    label = COUNTRIES[codes[0]] if len(codes) == 1 else "EU27" if mode == "EU27" else "Compare countries"
    return shared.energy_result(total, kcal, label, codes), rows


def country_demands(rows, kcal):
    return [shared.energy_result(row["people"], kcal, COUNTRIES[row["geo"]], [row["geo"]]) for row in rows]
