"""Population-only adapter for the simple, user-chosen energy edition."""
from pathlib import Path
import pandas as pd
from scenario_core import calculate_energy

COUNTRIES = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "HR": "Croatia",
    "CY": "Cyprus", "CZ": "Czechia", "DK": "Denmark", "EE": "Estonia",
    "FI": "Finland", "FR": "France", "DE": "Germany", "EL": "Greece",
    "HU": "Hungary", "IE": "Ireland", "IT": "Italy", "LV": "Latvia",
    "LT": "Lithuania", "LU": "Luxembourg", "MT": "Malta", "NL": "Netherlands",
    "PL": "Poland", "PT": "Portugal", "RO": "Romania", "SK": "Slovakia",
    "SI": "Slovenia", "ES": "Spain", "SE": "Sweden",
}
POPULATION_FILE = "processed/eurostat-demo_pjan-eu27-2025-age-sex.csv"


def source_root():
    local = Path(__file__).resolve().parent / "data/human-baseline-population"
    return local if local.is_dir() else Path(__file__).resolve().parents[3] / "data/human-baseline-population"


def value(frame, age, sex):
    rows = frame.loc[(frame.age == age) & (frame.sex == sex), "population"]
    if len(rows) != 1:
        raise ValueError(f"Expected one population value: {age}/{sex}")
    return int(rows.iloc[0])


def load_population():
    frame = pd.read_csv(source_root() / POPULATION_FILE)
    if not {"geo", "age", "sex", "time", "population"}.issubset(frame):
        raise ValueError("Missing population columns")
    if set(frame.geo) != set(COUNTRIES) or set(frame.time) != {2025}:
        raise ValueError("Expected the fixed EU27/2025 capture")
    if frame.duplicated(["geo", "age", "sex", "time"]).any():
        raise ValueError("Duplicate population observations")
    numbers = pd.to_numeric(frame.population, errors="raise")
    if numbers.isna().any() or (numbers < 0).any() or (numbers % 1 != 0).any():
        raise ValueError("Invalid population counts")
    frame["population"] = numbers.astype("int64")
    for code in COUNTRIES:
        row = demographics(frame, code)
        if row["female"] + row["male"] != row["people"]:
            raise ValueError("Source sex totals disagree")
        if row["children"] + row["adults"] + row["older"] + row["unknown"] != row["people"]:
            raise ValueError("Source age totals disagree")
    return frame


def demographics(frame, code):
    if code not in COUNTRIES:
        raise ValueError("Unsupported country")
    selected = frame.loc[frame.geo == code]
    ages = lambda start, end: sum(value(selected, f"Y{age}", "T") for age in range(start, end + 1))
    return {"geo": code, "people": value(selected, "TOTAL", "T"),
            "children": value(selected, "Y_LT1", "T") + ages(1, 17),
            "adults": ages(18, 70), "older": ages(71, 99) + value(selected, "Y_OPEN", "T"),
            "unknown": value(selected, "UNK", "T"),
            "female": value(selected, "TOTAL", "F"), "male": value(selected, "TOTAL", "M")}


def energy_result(people, kcal, name="Custom population", codes=None):
    codes = [] if codes is None else list(codes)
    if len(set(codes)) != len(codes) or not set(codes).issubset(COUNTRIES):
        raise ValueError("Choose distinct supported countries")
    population = {"schema_version": "1.0", "id": "selected-population",
                  "name": name, "origin": "official_adapter" if codes else "user_input",
                  "total_people": people, "sources": ["Eurostat DEMO_PJAN, 1 January 2025"] if codes else [],
                  "assumptions": ["Recorded population is not a complete count of everyone present."] if codes else ["User-entered headcount; demographics are not inferred."]}
    if codes:
        population["reference_date"] = "2025-01-01"
    scenario = {"schema_version": "1.0", "id": "uniform-energy-v1", "population_id": population["id"],
                "method_id": "flat_kcal_per_person_day", "method_version": "1.0",
                "parameters": {"kcal_per_person_day": kcal}, "sources": [],
                "time_basis": {"kind": "fixed_repeated_day", "days_per_year": 365, "months_per_year": 12},
                "assumptions": ["The same user-chosen kcal figure is applied to every person, including children and infants.",
                                "Any desired energy margin is included in the chosen figure; no extra buffer or maternal allowance is added.",
                                "Energy volume only, not individual needs, nutritional adequacy or delivered food."]}
    return calculate_energy(population, scenario)
