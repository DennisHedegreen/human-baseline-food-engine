"""Pure, catalog-driven energy-to-edible-mass conversion. No food names or I/O."""
from copy import deepcopy
import math


def number(value, label, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label}: expected finite number")
    if value < 0 or (positive and value == 0):
        raise ValueError(f"{label}: expected {'positive' if positive else 'non-negative'} number")
    return value


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: expected non-empty text")


def version(obj):
    if not isinstance(obj, dict) or obj.get("schema_version") != "1.0":
        raise ValueError("Unsupported object schema")


def validate_catalog(catalog):
    version(catalog)
    definitions = catalog["nutrients"]
    sources = catalog["sources"]
    if not isinstance(definitions, dict) or not definitions or not isinstance(sources, dict):
        raise ValueError("Expected nutrient and source registries")
    for key, definition in definitions.items():
        text(key, "nutrient ID")
        text(definition["unit"], "canonical nutrient unit")
        if not definition.get("names"):
            raise ValueError("Nutrient needs display names")
    for source_id, source in sources.items():
        text(source_id, "source ID")
        for field in ("url", "publisher", "retrieved_on", "reuse_status"):
            text(source[field], field)
    foods = catalog["foods"]
    if not isinstance(foods, list) or not foods:
        raise ValueError("Expected non-empty food catalog")
    ids = set()
    for food in foods:
        version(food)
        key = (food["id"], food["version"])
        for field in ("id", "version", "state", "edible_portion_description"):
            text(food[field], field)
        if key in ids or not food.get("names"):
            raise ValueError("Duplicate food version or missing names")
        ids.add(key)
        basis = food["basis"]
        if basis.get("unit") != "g" or basis.get("mass_kind") != "edible":
            raise ValueError("This converter requires grams of edible food")
        number(basis["amount"], "basis grams", positive=True)
        if food.get("item_default") is not None:
            item_equivalents({"food": food, "edible_kg": {"day": 0, "average_month": 0, "year": 0}},
                             food["item_default"], None)
        observations = food["observations"]
        if not isinstance(observations, dict):
            raise ValueError("Expected keyed nutrient observations")
        for nutrient_id, observation in observations.items():
            if nutrient_id not in definitions:
                raise ValueError("Unregistered nutrient")
            if observation["unit"] != definitions[nutrient_id]["unit"]:
                raise ValueError("Observation must use registered canonical unit")
            if observation["status"] == "unknown":
                if observation["value"] is not None:
                    raise ValueError("Unknown observation must be null")
            elif observation["status"] == "reported":
                number(observation["value"], nutrient_id)
                if observation.get("source_id") not in sources:
                    raise ValueError("Reported observation needs registered source")
            else:
                raise ValueError("Unsupported observation status")


def validate_demand(demand):
    """Accept the exported population-energy result, retaining its full provenance."""
    version(demand)
    basis = demand["energy_scenario"]["time_basis"]
    if basis.get("kind") != "fixed_repeated_day":
        raise ValueError("Only explicit repeated-day time basis is supported")
    days = number(basis["days_per_year"], "days per year", positive=True)
    months = number(basis["months_per_year"], "months per year", positive=True)
    daily = number(demand["kcal_day"], "daily kcal")
    annual = number(demand["kcal_year"], "annual kcal")
    monthly = number(demand["kcal_average_month"], "average-month kcal")
    if annual != daily * days or monthly != annual / months:
        raise ValueError("Inconsistent demand time arithmetic")
    return days, months


def per_person_kg(result):
    """Derived scenario average, not a separate dietary recommendation."""
    population = result["demand"].get("population")
    people = population.get("total_people") if isinstance(population, dict) else None
    if people is None:
        return None
    if type(people) is not int or people < 0:
        raise ValueError("Population headcount must be a non-negative integer")
    if people == 0:
        if result["demand"]["kcal_day"] != 0:
            raise ValueError("Non-zero energy cannot describe zero people")
        return None
    return {period: math.fsum(row["edible_kg"][period] for row in result["foods"]) / people
            for period in ("day", "average_month", "year")}


def item_equivalents(row, assumption, people):
    """Fractional mass-equivalent counts; never rounded procurement quantities."""
    if not isinstance(assumption, dict):
        raise ValueError("Item assumption must be an object")
    for field in ("id", "version", "label", "provenance"):
        text(assumption.get(field), field)
    food = row["food"]
    for field, expected in (("food_id", food["id"]), ("food_version", food["version"]),
                            ("state", food["state"]), ("mass_kind", "edible")):
        if assumption.get(field) != expected:
            raise ValueError(f"Item assumption has incompatible {field}")
    if assumption.get("status") not in ("user_assumption", "scenario_assumption", "source_reported"):
        raise ValueError("Item weight needs explicit provenance status")
    if assumption["status"] == "source_reported":
        text(assumption.get("source_url"), "item weight source URL")
    grams = number(assumption.get("grams_per_item"), "grams per item", positive=True)
    counts = {period: number(kg * 1000 / grams, "item equivalent")
              for period, kg in row["edible_kg"].items()}
    return {"assumption": deepcopy(assumption), "total": counts,
            "per_person": None if not people else {p: v / people for p, v in counts.items()},
            "interpretation": "approximate_fractional_mass_equivalent_not_procurement_count"}


def convert_energy(demand, catalog, shares, energy_nutrient_id, item_assumptions=None):
    """Shares are fractions of energy, never fractions of purchased mass."""
    days, months = validate_demand(demand)
    validate_catalog(catalog)
    energy_definition = catalog["nutrients"].get(energy_nutrient_id)
    if not energy_definition or energy_definition["unit"] != "kcal":
        raise ValueError("Select a registered kcal observation for conversion")
    if not isinstance(shares, list) or not shares:
        raise ValueError("Select at least one food version")
    foods = {(f["id"], f["version"]): f for f in catalog["foods"]}
    selected, seen = [], set()
    for share in shares:
        key = (share["food_id"], share["food_version"])
        fraction = number(share["energy_share"], "energy share", positive=True)
        if key not in foods or key in seen:
            raise ValueError("Unknown or duplicate food version")
        seen.add(key)
        food = foods[key]
        energy = food["observations"].get(energy_nutrient_id)
        if not energy or energy["status"] != "reported":
            raise ValueError("Missing energy cannot be treated as zero")
        density = number(energy["value"], "food energy", positive=True)
        kcal = demand["kcal_day"] * fraction
        grams = kcal / density * food["basis"]["amount"]
        number(grams * days, "calculated annual grams")
        selected.append({"food": deepcopy(food), "energy_share": fraction,
                         "kcal_day": kcal, "edible_g_day": grams})
    if not math.isclose(math.fsum(s["energy_share"] for s in shares), 1.0, rel_tol=0, abs_tol=1e-12):
        raise ValueError("Energy shares must sum to 1 (100%)")
    for row in selected:
        kg = row["edible_g_day"] / 1000
        row["edible_kg"] = {"day": kg, "average_month": kg * days / months, "year": kg * days}
        row["edible_tonnes"] = {period: value / 1000 for period, value in row["edible_kg"].items()}
    nutrients = {}
    for nutrient_id, definition in catalog["nutrients"].items():
        known, covered_share, missing = 0.0, 0.0, []
        for row in selected:
            food = row["food"]
            obs = food["observations"].get(nutrient_id)
            if obs and obs["status"] == "reported":
                known += row["edible_g_day"] / food["basis"]["amount"] * obs["value"]
                covered_share += row["energy_share"]
            else:
                missing.append({"food_id": food["id"], "food_version": food["version"]})
        number(known * days, "calculated nutrient amount")
        nutrients[nutrient_id] = {"unit": definition["unit"],
            "total_day": None if missing else known,
            "known_subtotal_day": known,
            "covered_energy_share": covered_share, "missing_foods": missing}
    result = {"schema_version": "1.0", "calculation_version": "food-energy-equivalent-0.3",
            "demand": deepcopy(demand), "catalog_snapshot": deepcopy(catalog),
            "energy_nutrient_id": energy_nutrient_id, "shares": deepcopy(shares),
            "foods": selected, "nutrients": nutrients,
            "total_edible_tonnes": {period: math.fsum(r["edible_tonnes"][period] for r in selected)
                                    for period in ("day", "average_month", "year")},
            "interpretation": "edible_mass_energy_equivalent_not_complete_diet_or_production_requirement",
            "purchased_mass": None, "price": None}
    result["per_person_edible_kg"] = per_person_kg(result)
    if item_assumptions is None:
        item_assumptions = []
    if not isinstance(item_assumptions, list):
        raise ValueError("Item assumptions must be a list")
    attached = set()
    for row in selected:
        row["item_equivalents"] = []
    population = demand.get("population")
    people = population.get("total_people") if isinstance(population, dict) else None
    for assumption in item_assumptions:
        if not isinstance(assumption, dict):
            raise ValueError("Item assumption must be an object")
        key = (assumption.get("food_id"), assumption.get("food_version"), assumption.get("id"))
        if key in attached:
            raise ValueError("Duplicate item assumption")
        attached.add(key)
        row = next((r for r in selected if (r["food"]["id"], r["food"]["version"]) == key[:2]), None)
        if row is None:
            raise ValueError("Item assumption must reference a selected food version")
        row["item_equivalents"].append(item_equivalents(row, assumption, people))
    return result
