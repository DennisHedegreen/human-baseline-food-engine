"""Local CLI adapter. Select food IDs from data; no food-specific calculations."""
import argparse
import json
from pathlib import Path
from food_core import convert_energy


def main():
    parser = argparse.ArgumentParser(description="Convert an exported energy scenario to edible food mass, not a complete diet.")
    parser.add_argument("demand", type=Path, help="Scenario JSON downloaded from the population tool")
    parser.add_argument("--catalog", type=Path, default=Path(__file__).with_name("catalog.json"))
    parser.add_argument("--food-id", required=True)
    parser.add_argument("--food-version", required=True)
    parser.add_argument("--energy-nutrient", default="energy")
    args = parser.parse_args()
    result = convert_energy(json.loads(args.demand.read_text()), json.loads(args.catalog.read_text()),
        [{"food_id": args.food_id, "food_version": args.food_version, "energy_share": 1.0}], args.energy_nutrient)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
