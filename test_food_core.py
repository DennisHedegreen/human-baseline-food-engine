import json
import math
from copy import deepcopy
from pathlib import Path
import unittest
from food_core import convert_energy


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads(Path(__file__).with_name("catalog.json").read_text())
        self.demand = {"schema_version": "1.0", "kcal_day": 3000, "kcal_year": 3000*365,
            "kcal_average_month": 3000*365/12,
            "energy_scenario": {"time_basis": {"kind": "fixed_repeated_day", "days_per_year": 365, "months_per_year": 12}},
            "population": {"total_people": 1}, "interpretation": "example"}
        f = self.catalog["foods"][0]
        self.shares = [{"food_id": f["id"], "food_version": f["version"], "energy_share": 1.0}]

    def calc(self, **kwargs):
        return convert_energy(kwargs.get("demand", self.demand), kwargs.get("catalog", self.catalog),
                              kwargs.get("shares", self.shares), "energy")

    def test_potato_example_and_periods(self):
        r = self.calc()
        self.assertAlmostEqual(r["foods"][0]["edible_kg"]["day"], 3000/770)
        self.assertAlmostEqual(r["total_edible_tonnes"]["year"], 3000/770*365/1000)
        self.assertAlmostEqual(r["total_edible_tonnes"]["average_month"], r["total_edible_tonnes"]["year"]/12)
        self.assertTrue(math.isclose(r["nutrients"]["energy"]["total_day"],3000))
        self.assertIsNone(r["nutrients"]["vitamin_c"]["total_day"])
        self.assertIsNone(r["price"])
        self.assertIsNone(r["purchased_mass"])

    def item_assumption(self):
        f = self.catalog["foods"][0]
        return {"id": "test-unit", "version": "1", "label": "synthetic unit",
                "food_id": f["id"], "food_version": f["version"], "state": f["state"],
                "mass_kind": "edible", "grams_per_item": 150,
                "status": "user_assumption", "provenance": "Synthetic test assumption"}

    def test_item_equivalents_and_export(self):
        a = self.item_assumption()
        r = convert_energy(self.demand, self.catalog, self.shares, "energy", [a])
        item = r["foods"][0]["item_equivalents"][0]
        for period in ("day", "average_month", "year"):
            self.assertAlmostEqual(item["total"][period], r["foods"][0]["edible_kg"][period]*1000/150)
            self.assertEqual(item["per_person"][period], item["total"][period])
        self.assertEqual(json.loads(json.dumps(r))["foods"][0]["item_equivalents"][0], item)
        a["grams_per_item"] = 999
        self.assertEqual(item["assumption"]["grams_per_item"], 150)
        self.assertEqual(self.calc()["foods"][0]["item_equivalents"], [])

    def test_item_equivalents_generic_and_missing_headcount(self):
        c = deepcopy(self.catalog)
        c["foods"][0].pop("item_default", None)
        c["foods"][0]["id"] = "synthetic-food"
        s = deepcopy(self.shares); s[0]["food_id"] = "synthetic-food"
        a = self.item_assumption(); a["food_id"] = "synthetic-food"; a["label"] = "cube"; a["grams_per_item"] = 5
        d = deepcopy(self.demand); del d["population"]
        r = convert_energy(d, c, s, "energy", [a])
        item = r["foods"][0]["item_equivalents"][0]
        self.assertIsNone(item["per_person"])
        self.assertAlmostEqual(item["total"]["day"], 3000/77*100/5)
        d["population"] = {"total_people": 0}
        for field in ("kcal_day", "kcal_year", "kcal_average_month"): d[field] = 0
        item = convert_energy(d, c, s, "energy", [a])["foods"][0]["item_equivalents"][0]
        self.assertEqual(item["total"]["day"], 0)
        self.assertIsNone(item["per_person"])

    def test_reject_incompatible_item_assumptions(self):
        for field, bad in (("grams_per_item", 0), ("grams_per_item", -1), ("grams_per_item", True),
                           ("grams_per_item", float("nan")), ("grams_per_item", float("inf")),
                           ("state", "incompatible"), ("mass_kind", "purchased"),
                           ("food_version", "other"), ("status", "invented"), ("label", ""),
                           ("provenance", ""), ("status", "source_reported")):
            a = self.item_assumption(); a[field] = bad
            with self.subTest(field=field, bad=bad), self.assertRaises(ValueError):
                convert_energy(self.demand, self.catalog, self.shares, "energy", [a])
        a = self.item_assumption()
        with self.assertRaises(ValueError):
            convert_energy(self.demand, self.catalog, self.shares, "energy", [a, a])

    def test_catalog_matches_shared_source_extract(self):
        local = Path(__file__).resolve().parent
        root = local if (local/"data/human-baseline-food").is_dir() else local.parents[2]
        expected = {"Energi (kcal)":"energy", "Protein":"protein", "Fedt":"fat",
                    "Tilgængelig kulhydrat":"available_carbohydrate", "Kostfibre":"fibre"}
        for food in self.catalog["foods"]:
            source=self.catalog["sources"][food["observations"]["energy"]["source_id"]]
            extract=json.loads((root/source["source_extract"]).read_text())
            self.assertEqual(extract["source_url"],source["url"])
            self.assertEqual(extract["record_id"],source["record_id"])
            self.assertEqual(extract["retrieved_on"],source["retrieved_on"])
            for observation in extract["observations"]:
                entry=food["observations"][expected[observation["source_label"]]]
                self.assertEqual(entry["value"],observation["value"])
                self.assertEqual(entry["unit"],observation["unit"])

    def test_separate_boiled_object_not_cooking_yield(self):
        food=next(f for f in self.catalog["foods"] if f["id"]=="dtu-801-potato-boiled")
        result=self.calc(shares=[{"food_id":food["id"],"food_version":food["version"],"energy_share":1}])
        self.assertAlmostEqual(result["foods"][0]["edible_kg"]["day"],3000/850)
        self.assertEqual(result["foods"][0]["food"]["state"],"boiled")
        self.assertIsNone(result["purchased_mass"])
        self.assertNotEqual(result["foods"][0]["edible_kg"]["day"],self.calc()["foods"][0]["edible_kg"]["day"])

    def test_per_person_periods_and_population_scaling(self):
        for people in (1,100,1000000):
            d=deepcopy(self.demand)
            d["population"]["total_people"]=people
            for key in ("kcal_day","kcal_year","kcal_average_month"): d[key]*=people
            average=self.calc(demand=d)["per_person_edible_kg"]
            self.assertAlmostEqual(average["day"],3000/770)
            self.assertAlmostEqual(average["year"],3000/770*365)
            self.assertAlmostEqual(average["average_month"],average["year"]/12)
        d=deepcopy(self.demand)
        del d["population"]
        self.assertIsNone(self.calc(demand=d)["per_person_edible_kg"])
        d=deepcopy(self.demand)
        d["population"]["total_people"]=0
        with self.assertRaises(ValueError): self.calc(demand=d)
        for key in ("kcal_day","kcal_year","kcal_average_month"): d[key]=0
        self.assertIsNone(self.calc(demand=d)["per_person_edible_kg"])
        d["population"]["total_people"]=True
        with self.assertRaises(ValueError): self.calc(demand=d)

    def test_rename_new_food_basis_and_nutrient_without_core_change(self):
        c = deepcopy(self.catalog)
        f = c["foods"][0]
        f.pop("item_default", None)
        f["id"] = "synthetic-test-not-food"; f["names"] = {"en": "Synthetic test only"}
        f["basis"]["amount"] = 200
        f["observations"]["energy"]["value"] = 200
        c["nutrients"]["test_mineral"] = {"unit":"mg", "names":{"en":"Synthetic mineral"}}
        f["observations"]["test_mineral"] = {"value":2, "unit":"mg", "status":"reported", "source_id":next(iter(c["sources"]))}
        s = [{"food_id":f["id"], "food_version":f["version"], "energy_share":1}]
        r = self.calc(catalog=c, shares=s)
        self.assertEqual(r["foods"][0]["edible_kg"]["day"],3)
        self.assertEqual(r["nutrients"]["test_mineral"]["total_day"],30)

    def test_mixture_and_missingness(self):
        c = deepcopy(self.catalog)
        second = deepcopy(c["foods"][0]); second["id"]="synthetic-second"
        second.pop("item_default", None)
        second["observations"]["energy"]["value"] = 154
        del second["observations"]["protein"]
        c["foods"].append(second)
        s=deepcopy(self.shares); s[0]["energy_share"]=0.5
        s.append({"food_id":second["id"], "food_version":second["version"], "energy_share":0.5})
        r=self.calc(catalog=c,shares=s)
        self.assertAlmostEqual(sum(x["edible_kg"]["day"] for x in r["foods"]),3000/770*0.75)
        self.assertIsNone(r["nutrients"]["protein"]["total_day"])
        self.assertEqual(r["nutrients"]["protein"]["covered_energy_share"],0.5)

    def test_zero_and_input_snapshot(self):
        d=deepcopy(self.demand)
        for key in ("kcal_day","kcal_year","kcal_average_month"): d[key]=0
        self.assertEqual(self.calc(demand=d)["total_edible_tonnes"]["day"],0)
        r=self.calc(); self.catalog["foods"][0]["observations"]["energy"]["value"]=1
        self.assertEqual(r["catalog_snapshot"]["foods"][0]["observations"]["energy"]["value"],77)
        self.assertEqual(json.loads(json.dumps(r))["demand"],self.demand)

    def test_reject_invalid(self):
        for val in (0,-1,True,float("nan"),float("inf"),None):
            c=deepcopy(self.catalog); c["foods"][0]["observations"]["energy"]["value"]=val
            with self.assertRaises(ValueError): self.calc(catalog=c)
        c=deepcopy(self.catalog); c["foods"][0]["observations"]["energy"]["unit"]="kJ"
        with self.assertRaises(ValueError): self.calc(catalog=c)
        for fraction in (0,0.5,2,True,float("nan")):
            s=deepcopy(self.shares); s[0]["energy_share"]=fraction
            with self.assertRaises(ValueError): self.calc(shares=s)
        with self.assertRaises(ValueError): self.calc(shares=self.shares+self.shares)
        s=deepcopy(self.shares); s[0]["food_version"]="unrecorded"
        with self.assertRaises(ValueError): self.calc(shares=s)
        d=deepcopy(self.demand); d["kcal_year"]+=1
        with self.assertRaises(ValueError): self.calc(demand=d)

    def test_catalog_item_defaults_are_explicit_and_validated(self):
        for food in self.catalog["foods"]:
            assumption = food["item_default"]
            self.assertEqual(assumption["label"], "potato")
            self.assertEqual(assumption["status"], "scenario_assumption")
            self.assertIn("not a measured average", assumption["provenance"])
            result = convert_energy(self.demand, self.catalog,
                [{"food_id":food["id"], "food_version":food["version"], "energy_share":1}],
                "energy", [assumption])
            self.assertEqual(result["foods"][0]["item_equivalents"][0]["assumption"], assumption)
        broken = deepcopy(self.catalog)
        broken["foods"][0]["item_default"]["state"] = "boiled"
        with self.assertRaises(ValueError): self.calc(catalog=broken)


if __name__ == "__main__":
    unittest.main()
