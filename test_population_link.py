import json
import unittest
from pathlib import Path
from population_link import shared, build_demand, country_demands, COUNTRIES, load_population
from food_core import convert_energy


class SharedLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame=load_population()

    def test_all_countries_exact_original_result(self):
        for code in COUNTRIES:
            result,rows=build_demand("Country",3000,codes=[code],frame=self.frame)
            original=shared.energy_result(shared.demographics(self.frame,code)["people"],3000,COUNTRIES[code],[code])
            self.assertEqual(result,original)
            self.assertEqual(len(rows),1)

    def test_eu_and_comparison_additivity_through_food_core(self):
        catalog=json.loads(Path(__file__).with_name("catalog.json").read_text())
        food=catalog["foods"][0]
        shares=[{"food_id":food["id"],"food_version":food["version"],"energy_share":1}]
        for mode,codes in [("EU27",None),("Compare countries",["DK","DE","PL"])]:
            result,rows=build_demand(mode,4000,codes=codes,frame=self.frame)
            singles=country_demands(rows,4000)
            self.assertEqual(result["kcal_day"],sum(d["kcal_day"] for d in singles))
            mass=convert_energy(result,catalog,shares,"energy")
            single_masses=[convert_energy(d,catalog,shares,"energy") for d in singles]
            self.assertAlmostEqual(mass["total_edible_tonnes"]["day"],sum(x["total_edible_tonnes"]["day"] for x in single_masses),places=6)
            self.assertEqual(len(rows),27 if mode=="EU27" else 3)

    def test_custom_calls_existing_kernel_and_zero(self):
        for people,kcal in [(100,4000),(0,3000),(100,0)]:
            result,rows=build_demand("Custom population",kcal,people=people,name="Own scenario")
            self.assertEqual(result,shared.energy_result(people,kcal,"Own scenario"))
            self.assertEqual(rows,[])
        for people in [-1,True]:
            with self.assertRaises(ValueError): build_demand("Custom population",3000,people=people)

    def test_reject_empty_duplicate_unknown(self):
        for codes in [[],["DK","DK"],["not-a-country"]]:
            with self.assertRaises(ValueError): build_demand("Compare countries",3000,codes=codes,frame=self.frame)


if __name__=="__main__": unittest.main()
