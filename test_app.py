import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent


class UITests(unittest.TestCase):
    def test_explicit_item_weight_and_food_state_reset(self):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        at.radio(key="scenario_input").set_value("Illustrative example").run()
        self.assertTrue(at.checkbox(key="show_items").value)
        self.assertEqual(at.text_input[0].value, "potato")
        self.assertEqual(len(at.metric), 15)
        grams = next(x for x in at.number_input if x.label == "Edible grams per item")
        grams.set_value(200.0).run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.metric), 15)
        self.assertIn("19.48", at.metric[12].value)
        self.assertTrue(all(x.help for x in at.metric))
        catalog = json.loads((ROOT / "catalog.json").read_text())
        food = catalog["foods"][1]
        at.selectbox[0].set_value((food["id"], food["version"])).run()
        self.assertEqual(len(at.metric), 15)
        self.assertEqual(next(x for x in at.number_input if x.label == "Edible grams per item").value, 150)
        at.checkbox(key="show_items").set_value(False).run()
        self.assertEqual(len(at.metric), 9)

    def test_example_units_and_empty_upload(self):
        at = AppTest.from_file(str(ROOT / "app.py"),default_timeout=30).run()
        at.radio(key="scenario_input").set_value("Illustrative example").run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.metric), 15)
        self.assertIn("3 896.10", at.metric[3].value)
        self.assertTrue(all(x.help for x in at.metric))
        at.radio(key="mass_units").set_value("Kilograms").run()
        self.assertIn("3.90 million", at.metric[3].value)
        at.radio(key="scenario_input").set_value("Upload population-tool JSON").run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.metric), 0)
        self.assertTrue(any("not silently substituted" in x.value for x in at.info))

    def test_catalog_drives_names_density_and_nutrient_rows(self):
        catalog = json.loads((ROOT / "catalog.json").read_text())
        food = catalog["foods"][0]
        food.pop("item_default", None)
        food["id"] = "synthetic-ui-test"
        food["names"] = {"en":"Synthetic food — test only"}
        food["observations"]["energy"]["value"] = 100
        catalog["nutrients"]["new_parameter"] = {"names":{"en":"New test parameter"},"unit":"mg"}
        food["observations"]["new_parameter"] = {"value":None,"unit":"mg","status":"unknown"}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            path.write_text(json.dumps(catalog))
            with patch.dict(os.environ, {"HB_FOOD_CATALOG":str(path)}):
                at = AppTest.from_file(str(ROOT / "app.py"),default_timeout=30).run()
                at.radio(key="scenario_input").set_value("Illustrative example").run()
                self.assertFalse(at.exception)
                self.assertIn("Synthetic food", at.selectbox[0].options[0])
                self.assertIn("3 000.00", at.metric[3].value)
                self.assertIn("New test parameter", str(at.table[0].value))

    def test_direct_population_modes(self):
        at = AppTest.from_file(str(ROOT / "app.py"),default_timeout=30).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.radio(key="scenario_input").value, "Country")
        self.assertEqual(at.selectbox[0].value, "DK")
        for label in ["Compare countries", "EU27", "Custom population"]:
            at.radio(key="scenario_input").set_value(label).run()
            self.assertFalse(at.exception)
            self.assertEqual(len(at.metric),15)
            if label != "Custom population":
                self.assertEqual(len(at.dataframe),1)
        at.number_input(key="custom_people").set_value(100).run()
        at.number_input(key="uniform_kcal").set_value(4000.0).run()
        self.assertIn("400 000",at.metric[0].value)
        self.assertIn("0.52",at.metric[3].value)
        self.assertIn("5.19",at.metric[6].value)
        at.number_input(key="custom_people").set_value(0).run()
        self.assertIn("0.00",at.metric[0].value)
        self.assertIn("0.00",at.metric[3].value)
        self.assertEqual(at.metric[6].value,"—")
        at.radio(key="scenario_input").set_value("Compare countries").run()
        at.multiselect[0].set_value([]).run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.metric),0)

    def test_boiled_variant_is_catalog_driven(self):
        catalog=json.loads((ROOT/"catalog.json").read_text())
        food=next(f for f in catalog["foods"] if f["state"]=="boiled")
        at=AppTest.from_file(str(ROOT/"app.py"),default_timeout=30).run()
        at.radio(key="scenario_input").set_value("Illustrative example").run()
        at.selectbox[0].set_value((food["id"],food["version"])).run()
        self.assertFalse(at.exception)
        self.assertIn("3 529.41",at.metric[3].value)
        self.assertIn("boiled",at.metric[3].help)
        self.assertIn("3.53",at.metric[6].value)

    def test_about_navigation_and_population_link(self):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        at.radio(key="view_mode").set_value("About & sources").run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.metric), 0)
        self.assertTrue(any("Two connected tools" in x.value for x in at.subheader))
        self.assertTrue(any("150 g" in x.value for x in at.markdown))
        at.radio(key="view_mode").set_value("Food quantities").run()
        self.assertEqual(len(at.metric), 15)


if __name__ == "__main__":
    unittest.main()
