"""Versioned, JSON-compatible population/energy contract. No UI or source I/O."""
from copy import deepcopy
import math

SCHEMA_VERSION = "1.0"
CALCULATION_VERSION = "intake-energy-1.1"


def text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")


def finite_nonnegative(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{field} must be finite and non-negative")


def count(value, field):
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")


def fields(obj, required, optional=()):
    if not isinstance(obj, dict) or set(obj) - set(required) - set(optional) or set(required) - set(obj):
        raise ValueError(f"Expected fields {sorted(required)}; optional {sorted(optional)}")


def metadata(obj):
    if obj["schema_version"] != SCHEMA_VERSION:
        raise ValueError("Unsupported schema version")
    text(obj["id"], "id")
    if not isinstance(obj["sources"], list) or not isinstance(obj["assumptions"], list):
        raise ValueError("Sources and assumptions must be lists")
    for source in obj["sources"]:
        text(source, "source reference")
    for assumption in obj["assumptions"]:
        text(assumption, "assumption")


def validate_population(obj):
    fields(obj, {"schema_version", "id", "name", "origin", "total_people", "sources", "assumptions"},
           {"reference_date", "demographic_groups", "demographic_coverage", "member_ids"})
    metadata(obj)
    text(obj["name"], "name")
    if obj["origin"] not in ("official_adapter", "user_input", "composite"):
        raise ValueError("Unknown population origin")
    count(obj["total_people"], "total_people")
    if obj["origin"] == "official_adapter" and not obj["sources"]:
        raise ValueError("Official input requires source references")
    if "reference_date" in obj and obj["reference_date"] is not None:
        from datetime import date
        date.fromisoformat(obj["reference_date"])
    members = obj.get("member_ids", [])
    if not isinstance(members, list) or len(set(members)) != len(members):
        raise ValueError("Composite member IDs must be unique")
    for member in members:
        text(member, "member ID")
    if obj["origin"] == "composite" and (not members or not obj["assumptions"]):
        raise ValueError("Composite input requires members and explicit aggregation assumptions")
    if members and obj["origin"] != "composite":
        raise ValueError("Only composite input may have members")
    groups = obj.get("demographic_groups")
    coverage = obj.get("demographic_coverage")
    if groups is None:
        if coverage is not None:
            raise ValueError("Coverage requires demographic groups")
        return
    if not isinstance(groups, list) or not groups or coverage not in ("complete", "partial"):
        raise ValueError("Groups need explicit complete/partial coverage")
    ids = set()
    for group in groups:
        fields(group, {"id", "age_min", "age_max", "source_sex", "people"})
        text(group["id"], "group ID")
        if group["id"] in ids:
            raise ValueError("Duplicate demographic group")
        ids.add(group["id"])
        count(group["age_min"], "age_min")
        if group["age_max"] is not None:
            count(group["age_max"], "age_max")
            if group["age_max"] < group["age_min"]:
                raise ValueError("Inverted age interval")
        text(group["source_sex"], "source_sex")
        count(group["people"], "group people")
    for i, left in enumerate(groups):
        for right in groups[i + 1:]:
            overlap = max(left["age_min"], right["age_min"]) <= min(
                left["age_max"] if left["age_max"] is not None else math.inf,
                right["age_max"] if right["age_max"] is not None else math.inf)
            if overlap and (left["source_sex"] == right["source_sex"] or "ALL" in (left["source_sex"], right["source_sex"])):
                raise ValueError("Overlapping demographic groups")
    represented = sum(group["people"] for group in groups)
    if represented > obj["total_people"] or (coverage == "complete" and represented != obj["total_people"]):
        raise ValueError("Demographic counts disagree with population total")


def validate_energy_scenario(obj):
    fields(obj, {"schema_version", "id", "population_id", "method_id", "method_version", "parameters", "time_basis", "sources", "assumptions"})
    metadata(obj)
    text(obj["population_id"], "population_id")
    if obj["method_version"] != "1.0":
        raise ValueError("Unsupported method version")
    if obj["method_id"] == "flat_kcal_per_person_day":
        fields(obj["parameters"], {"kcal_per_person_day"})
        finite_nonnegative(obj["parameters"]["kcal_per_person_day"], "kcal_per_person_day")
    elif obj["method_id"] == "reference_component_sum":
        fields(obj["parameters"], {"reference_id", "reference_version", "components"})
        text(obj["parameters"]["reference_id"], "reference_id")
        text(obj["parameters"]["reference_version"], "reference_version")
        components = obj["parameters"]["components"]
        if not isinstance(components, list) or not components or not obj["sources"] or not obj["assumptions"]:
            raise ValueError("Reference sums require components, sources and assumptions")
        ids = set()
        for component in components:
            fields(component, {"id", "kcal_day"})
            text(component["id"], "component ID")
            if component["id"] in ids:
                raise ValueError("Duplicate energy component")
            ids.add(component["id"])
            finite_nonnegative(component["kcal_day"], "component energy")
    else:
        raise ValueError("Unsupported energy method")
    if obj["time_basis"] != {"kind": "fixed_repeated_day", "days_per_year": 365, "months_per_year": 12}:
        raise ValueError("v1.0 uses 365 repeated days and 12 average months only")


def daily_components(population, scenario):
    if scenario["method_id"] == "flat_kcal_per_person_day":
        return [{"id": "flat_intake", "kcal_day": population["total_people"] * scenario["parameters"]["kcal_per_person_day"]}]
    return deepcopy(scenario["parameters"]["components"])


def calculate_energy(population, scenario):
    validate_population(population)
    validate_energy_scenario(scenario)
    if population["id"] != scenario["population_id"]:
        raise ValueError("Scenario references a different population")
    components = daily_components(population, scenario)
    daily = sum(component["kcal_day"] for component in components)
    if population["total_people"] == 0 and daily != 0:
        raise ValueError("Non-zero intake cannot describe an empty population")
    annual = daily * scenario["time_basis"]["days_per_year"]
    finite_nonnegative(annual, "calculated annual energy")
    result = {
        "schema_version": SCHEMA_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "population": deepcopy(population), "energy_scenario": deepcopy(scenario),
        "kcal_day": daily, "kcal_year": annual, "kcal_average_month": annual / 12,
        "kcal_per_person_day": None if population["total_people"] == 0 else daily / population["total_people"],
        "components": components,
        "interpretation": "intake_energy_scenario_not_validated_food_production_requirement",
    }
    validate_energy_result(result)
    return result


def validate_energy_result(obj):
    fields(obj, {"schema_version", "calculation_version", "population", "energy_scenario", "kcal_day", "kcal_year", "kcal_average_month", "kcal_per_person_day", "components", "interpretation"})
    validate_population(obj["population"])
    validate_energy_scenario(obj["energy_scenario"])
    if obj["schema_version"] != SCHEMA_VERSION or obj["calculation_version"] != CALCULATION_VERSION:
        raise ValueError("Unsupported result version")
    if obj["population"]["id"] != obj["energy_scenario"]["population_id"]:
        raise ValueError("Result identity mismatch")
    if obj["interpretation"] != "intake_energy_scenario_not_validated_food_production_requirement":
        raise ValueError("Result interpretation mismatch")
    components = daily_components(obj["population"], obj["energy_scenario"])
    expected = sum(component["kcal_day"] for component in components)
    if not obj["population"]["total_people"] and expected:
        raise ValueError("Non-zero intake cannot describe an empty population")
    for key, value in (("kcal_day", expected), ("kcal_year", expected * 365), ("kcal_average_month", expected * 365 / 12)):
        finite_nonnegative(obj[key], key)
        if not math.isclose(obj[key], value, rel_tol=0, abs_tol=1e-9):
            raise ValueError(f"Inconsistent result: {key}")
    average = obj["kcal_per_person_day"]
    if not obj["population"]["total_people"]:
        if average is not None:
            raise ValueError("Empty population average must be null")
    else:
        finite_nonnegative(average, "average")
        if not math.isclose(average, expected / obj["population"]["total_people"], rel_tol=1e-12):
            raise ValueError("Inconsistent average")
    if obj["components"] != components:
        raise ValueError("Inconsistent components")
