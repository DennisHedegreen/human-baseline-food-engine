"""Local food-mass UI: all food/nutrient selectors are driven by catalog data."""
import json
import os
from pathlib import Path
import streamlit as st
from food_core import convert_energy, validate_catalog, validate_demand
from population_link import COUNTRIES, load_population, build_demand, country_demands

ROOT = Path(__file__).resolve().parent
CATALOG_PATH = Path(os.environ.get("HB_FOOD_CATALOG", ROOT / "catalog.json"))
POPULATION_APP_URL = os.environ.get("HB_POPULATION_APP_URL", "https://human-baseline-population-energy-bvvlgn8pezxxdgrcuphkns.streamlit.app/")


@st.cache_data
def population_data():
    return load_population()


def exact(value):
    return f"{value:,.6f}".rstrip("0").rstrip(".").replace(",", " ")


def readable(value):
    for divisor, label in [(1e12, "trillion"), (1e9, "billion"), (1e6, "million")]:
        if abs(value) >= divisor:
            return f"≈ {value/divisor:,.2f} {label}"
    return f"≈ {value:,.2f}".replace(",", " ")


def parse_demand(raw):
    if len(raw) > 2_000_000:
        raise ValueError("Scenario exceeds the 2 MB local input limit")
    demand = json.loads(raw)
    validate_demand(demand)
    return demand


def display_name(obj):
    return obj["names"].get("en") or next(iter(obj["names"].values()))


def main():
    st.set_page_config(page_title="Human Baseline · Food quantities", layout="wide")
    manifest_path = ROOT / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    approved_payload = manifest.get("status") == "approved_release_payload"
    st.markdown("""<style>
    .stApp{background:#f7f7fa;color:#252530} .stApp h1{font-family:Georgia,serif!important;font-weight:400!important}
    div[data-testid=stMetric]{background:white;border:1px solid #dadce8;padding:16px}
    div[data-testid=stMetricValue]{font-family:Georgia,serif;font-size:1.75rem}
    .stMainBlockContainer{max-width:1500px} .intro{border-left:3px solid #19d55b;padding:12px 20px;margin-bottom:22px}
    @media(max-width:600px){h1{font-size:1.9rem!important;white-space:normal!important;overflow-wrap:anywhere}
    [data-testid=stMarkdownContainer] p{white-space:normal!important;overflow-wrap:anywhere}}
    </style>""", unsafe_allow_html=True)
    with st.sidebar:
        st.caption("HEDEGREEN RESEARCH · HUMAN BASELINE")
        view = st.radio("View", ["Food quantities", "About & sources"], key="view_mode")
        st.caption(f"02 · Food quantities · {manifest['release_version']} · English interface" if approved_payload else
                   "02 · Food quantities · local development · English interface")
        st.link_button("01 · Population & energy", POPULATION_APP_URL)
    st.title("Human Baseline" if view == "Food quantities" else "About & sources")
    st.caption("Population and dietary energy → equivalent food quantities")
    st.markdown('<div class="intro">The second layer: explore what a population’s energy scenario means '
                'in food weight and approximate item counts.</div>', unsafe_allow_html=True)
    st.write("Choose a population and daily kcal figure, then see the equivalent mass of one selected food. "
             "Population data and energy arithmetic are reused directly from the first-layer calculator. "
             "It does not choose a diet or establish what farms, shops or delivery systems must supply.")
    st.caption("English interface · single-food energy equivalents, not a complete diet" if approved_payload else
               "Local prototype · English interface · no change to the published population calculator")
    if manifest:
        st.caption(f"Version: {manifest['release_version']} · reproducible source release" if approved_payload else
                   f"Version: {manifest['release_version']} · {manifest['status']}. Snapshot, not a hosted-publication receipt.")
    try:
        catalog = json.loads(CATALOG_PATH.read_text())
        validate_catalog(catalog)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        st.error(f"Catalog cannot be used: {exc}")
        st.stop()
    if view == "About & sources":
        st.subheader("Two connected tools")
        st.write("App 1 establishes population × chosen kcal per person, with country, comparison, EU27 and custom inputs. "
                 "App 2 reuses that same calculation and translates its energy into one food's mass and approximate item counts. "
                 "You can calculate here directly or import App 1's scenario JSON; no totals need to be typed again.")
        st.link_button("Open App 1 · Population & energy", POPULATION_APP_URL)
        st.subheader("The existing population and kcal layer")
        st.write("Country, comparison, EU27 and custom headcount call the same simple_model and scenario_core "
                 "as the first-layer tool. The same fixed Eurostat capture is read, without copied country totals. "
                 "One selected kcal figure applies to everyone; no hidden buffer or maternal allowance is added.")
        st.markdown("[Eurostat · DEMO_PJAN population by age and sex](https://ec.europa.eu/eurostat/databrowser/view/demo_pjan/default/table)")
        st.caption("Population snapshot: 1 January 2025. Eurostat is not responsible for this adaptation or its results.")
        st.subheader("A conversion, not a complete diet")
        st.write("For each selected food: grams per day = scenario kcal per day ÷ the source's kcal amount "
                 "× its mass basis in grams. This screen assigns 100% of energy to one food. "
                 "Energy shares are not mass shares.")
        st.write("Annual mass repeats the scenario day by its declared days per year. Average month is annual "
                 "mass divided by its declared months per year, not a particular calendar month. "
                 "Unknown nutrients remain unknown; a reported zero is distinct from a missing value.")
        st.write("Food state and composition basis travel with the selected object. Raw and cooked foods need "
                 "separate source-backed objects. No cooking yield, peeling loss, purchased-weight factor, "
                 "cost or production model is inferred.")
        st.subheader("Approximate item counts")
        st.write("Item count = edible grams ÷ edible grams per item in the same food state. The potato default of 150 g "
                 "is an editable illustrative assumption, not a measured average or DTU item-size observation. "
                 "Counts and weight assumptions are exported with provenance. Fractional equivalents are not purchase quantities.")
        for source_id, source in catalog["sources"].items():
            st.markdown(f"**{source['publisher']}** · [{source_id}]({source['url']})")
            st.write(f"Retrieved: {source['retrieved_on']}. Database release: "
                     f"{source.get('database_version') or 'not recorded'}.")
            st.write(source["reuse_status"])
        st.caption("Small attributed numerical extracts only; no general database redistribution licence is claimed." if approved_payload else
                   "Source attribution and a local numeric extract are not a completed public-release review.")
        return
    with st.container():
        st.subheader("1. Population and energy")
        mode = st.radio("Scenario input", ["Country", "Compare countries", "EU27", "Custom population",
                        "Upload population-tool JSON", "Illustrative example"],
                        horizontal=True, key="scenario_input", help="Build directly using the existing population/calculation layer. JSON import remains optional.")
        population_rows = []
        demand = None
        if mode == "Illustrative example":
            raw = (ROOT / "example-demand.json").read_bytes()
            st.info("Example only: the scenario file supplies the headcount and chosen kcal. No official country is implied.")
        elif mode == "Upload population-tool JSON":
            upload = st.file_uploader("Population-tool scenario JSON", type=["json"],
                                      help="Download this scenario · JSON in the published population calculator, then upload it here.")
            if upload is None:
                st.info("Upload a scenario to calculate. The example is not silently substituted.")
                st.stop()
            raw = upload.getvalue()
        else:
            with st.container(border=True):
                codes = []
                people = None
                name = None
                if mode == "Country":
                    codes = [st.selectbox("Country", list(COUNTRIES), index=list(COUNTRIES).index("DK"),
                                         format_func=lambda code: f"{COUNTRIES[code]} · {code}", key="selected_country",
                                         help="Country options and population values are reused from the first layer's official adapter.")]
                elif mode == "Compare countries":
                    codes = st.multiselect("Countries to compare", list(COUNTRIES), default=["DK", "DE", "PL"],
                                           format_func=lambda code: f"{COUNTRIES[code]} · {code}", key="selected_countries",
                                           help="The total includes each selected country once. Per-country results appear below.")
                    if not codes:
                        st.info("Choose at least one country; no previous calculation is substituted.")
                        st.stop()
                elif mode == "EU27":
                    st.write("All 27 countries in the same fixed Eurostat population capture.")
                elif mode == "Custom population":
                    left, right = st.columns(2)
                    name = left.text_input("Population name", "Custom population", key="custom_name")
                    people = right.number_input("Number of people", min_value=0, value=1000000, step=1000,
                                                key="custom_people", help="User-entered headcount, not inferred country demographics.")
                kcal = st.number_input("Chosen kcal/person/day", min_value=0.0, value=3000.0, step=100.0,
                                       key="uniform_kcal", help="An editable planning choice for every person, not a nutritional recommendation. "
                                       "Any desired energy margin is already inside this figure; no separate infant or maternal allowance.")
            try:
                demand, population_rows = build_demand(mode, kcal, codes, people, name,
                    frame=None if mode == "Custom population" else population_data())
            except (OSError, ValueError, TypeError, KeyError) as exc:
                st.error(f"Population scenario cannot be calculated: {exc}")
                st.stop()
        try:
            demand = parse_demand(raw) if demand is None else demand
        except (ValueError, TypeError, KeyError, UnicodeError) as exc:
            st.error(f"Scenario cannot be used: {exc}")
            st.stop()
        if population_rows:
            st.caption("Official population: 1 January 2025. Age and source-sex groups are descriptive context; they do not alter the uniform kcal input.")
            with st.expander("Who is counted?"):
                st.table([{"Country": COUNTRIES[row["geo"]], "Population": row["people"],
                           "Children 0–17": row["children"], "Adults 18–70": row["adults"],
                           "Older people 71+": row["older"], "Female": row["female"], "Male": row["male"],
                           "Unknown age": row["unknown"]} for row in population_rows])
        for col, field, label in zip(st.columns(3), ["kcal_day", "kcal_average_month", "kcal_year"],
                                    ["Scenario energy · kcal/day", "Scenario energy · kcal/average month", "Scenario energy · kcal/year"]):
            col.metric(label, readable(demand[field]),
                       help=f"Exact first-layer result: {exact(demand[field])} kcal. "
                       "Same chosen kcal for every person; an average month is annual energy divided by declared months/year. "
                       "Not independently verified individual needs.")
        with st.expander("Inspect the input scenario"):
            st.json(demand)
        st.download_button("Download energy scenario · JSON", json.dumps(demand, ensure_ascii=False, indent=2, allow_nan=False),
                           "human-baseline-energy-scenario.json", mime="application/json")
        st.subheader("2. Select a food object")
        foods = catalog["foods"]
        keys = [(food["id"], food["version"]) for food in foods]
        by_key = dict(zip(keys, foods))
        key = st.selectbox("Food and observation version", keys,
                           format_func=lambda k: f"{display_name(by_key[k])} · {by_key[k]['state']} · {k[1]}",
                           help="Options come from catalog objects. Names never choose the formula.")
        energy_ids = [k for k, definition in catalog["nutrients"].items() if definition["unit"] == "kcal"]
        if not energy_ids:
            st.error("Catalog has no registered kcal parameter.")
            st.stop()
        energy_id = st.selectbox("Energy observation", energy_ids,
            format_func=lambda k: display_name(catalog["nutrients"][k]),
            help="The selected source parameter defines energy density; no implicit kJ/kcal conversion.")
        food = by_key[key]
        default_item = food.get("item_default") or {}
        item_assumptions = []
        if st.checkbox("Show approximate item counts", value=bool(default_item), key="show_items",
                       help="Convert edible mass to units using an explicit weight per item. No standard item size is assumed."):
            st.caption(f"Weight must describe the edible part in the selected state: {food['state']}. "
                       "Item weights are scenario assumptions, not DTU measurements of item size.")
            if default_item:
                st.caption(default_item["provenance"])
            label = st.text_input("Item label", value=default_item.get("label", "item"), key=f"item_label_{key}",
                                  help="For example potato, sugar cube or serving. A label does not change food composition.")
            grams = st.number_input("Edible grams per item", min_value=0.0, value=float(default_item.get("grams_per_item", 0)),
                                    key=f"item_grams_{key}",
                                    help="Enter a positive weight in the selected food state. Zero means not supplied; no count is calculated.")
            if grams > 0 and label.strip():
                if default_item and label.strip() == default_item["label"] and grams == default_item["grams_per_item"]:
                    item_assumptions = [default_item]
                else:
                    item_assumptions = [{"id": "user-item", "version": "1", "label": label.strip(),
                        "food_id": key[0], "food_version": key[1], "state": food["state"],
                        "mass_kind": "edible", "grams_per_item": grams,
                        "status": "user_assumption", "provenance": "Entered in this scenario; not a source-reported standard size"}]
            else:
                st.info("Enter an item label and a positive edible weight to show approximate counts.")
        try:
            result = convert_energy(demand, catalog,
                [{"food_id": key[0], "food_version": key[1], "energy_share": 1.0}], energy_id,
                item_assumptions=item_assumptions)
        except (ValueError, TypeError, KeyError) as exc:
            st.error(f"Conversion cannot be calculated: {exc}")
            st.stop()
        obs = food["observations"][energy_id]
        st.write(f"Source density: {exact(obs['value'])} {obs['unit']} per "
                 f"{exact(food['basis']['amount'])} {food['basis']['unit']}. "
                 "This example assigns all scenario energy to this food.")
        st.caption(food["edible_portion_description"])
        for note in food.get("notes", []):
            st.caption(note)
        unit = st.radio("Display mass in", ["Metric tonnes", "Kilograms"], horizontal=True,
                        key="mass_units", help="One metric tonne = 1,000 kg. Display units do not change the calculation.")
        amounts = result["foods"][0]["edible_tonnes" if unit == "Metric tonnes" else "edible_kg"]
        suffix = "tonnes" if unit == "Metric tonnes" else "kg"
        basis = demand["energy_scenario"]["time_basis"]
        st.subheader("3. Equivalent food mass")
        st.markdown("**Whole population**")
        cols = st.columns(3)
        for col, period, title in zip(cols, ["day", "average_month", "year"], ["Daily", "Average month", "Annual"]):
            col.metric(f"{title} · {suffix}", readable(amounts[period]),
                       help=f"Exact: {exact(amounts[period])} {suffix}. Edible mass in state '{food['state']}', "
                       f"not harvested/purchased weight. Time basis: {basis['days_per_year']} repeated days/year, "
                       f"{basis['months_per_year']} average months/year.")
        st.markdown("**Per person · scenario average**")
        per_person = result["per_person_edible_kg"]
        for col, period, title in zip(st.columns(3), ["day", "average_month", "year"], ["Daily", "Average month", "Annual"]):
            col.metric(f"{title} · kg/person", "—" if per_person is None else readable(per_person[period]),
                       help="Unavailable for zero or unknown headcount." if per_person is None else
                       f"Exact: {exact(per_person[period])} kg/person. Total edible mass divided by the scenario headcount "
                       f"({exact(demand['population']['total_people'])} people). Food state: {food['state']}. "
                       f"Time basis: {basis['days_per_year']} repeated days/year and {basis['months_per_year']} average months/year. "
                       "A scenario average, not an individual diet recommendation.")
        if per_person is None:
            st.caption("Per-person mass is unavailable when the headcount is zero or not supplied; no division by zero or invented population.")
        for equivalent in result["foods"][0]["item_equivalents"]:
            assumption = equivalent["assumption"]
            st.subheader("Approximate item equivalents")
            st.caption(f"Scenario assumption: 1 {assumption['label']} = {exact(assumption['grams_per_item'])} g edible mass "
                       f"in state '{assumption['state']}'. Not a measured standard size. {assumption['provenance']} Counts may be fractional; "
                       "they are mass equivalents, not a purchase order.")
            for scope, heading in (("total", "Whole population"), ("per_person", "Per person · scenario average")):
                st.markdown(f"**{heading}**")
                counts = equivalent[scope]
                for col, period, title in zip(st.columns(3), ["day", "average_month", "year"], ["Daily", "Average month", "Annual"]):
                    col.metric(f"{title} · {assumption['label']} equivalents", "—" if counts is None else readable(counts[period]),
                               help="Unavailable for zero or unknown headcount." if counts is None else
                               f"Exact: {exact(counts[period])}. Edible grams ÷ {exact(assumption['grams_per_item'])} g/item; "
                               f"{basis['days_per_year']} repeated days/year, {basis['months_per_year']} average months/year. "
                               "Based on the displayed weight assumption, not independently measured item counts.")
        st.warning("Energy-equivalent mass only. This is not a nutritionally complete diet or a production requirement.")
        if len(population_rows) > 1:
            st.subheader("Compare countries using the same food and kcal choice")
            comparison = []
            for country_demand in country_demands(population_rows, kcal):
                country_mass = convert_energy(country_demand, catalog, result["shares"], energy_id)
                comparison.append({"Country": country_demand["population"]["name"],
                    "Population": country_demand["population"]["total_people"],
                    "kcal/day": country_demand["kcal_day"],
                    "Edible tonnes/day": country_mass["total_edible_tonnes"]["day"],
                    "Edible tonnes/average month": country_mass["total_edible_tonnes"]["average_month"],
                    "Edible tonnes/year": country_mass["total_edible_tonnes"]["year"]})
            st.dataframe(comparison, hide_index=True, width="stretch", column_config={
                "Population": st.column_config.NumberColumn(help="Official captured population, not a forecast", format="localized"),
                "kcal/day": st.column_config.NumberColumn(help="Existing first-layer energy_result, with the same chosen kcal for each country", format="localized"),
                **{field: st.column_config.NumberColumn(help="Food energy-equivalent mass in the selected state, not farm output", format="localized")
                   for field in ["Edible tonnes/day", "Edible tonnes/average month", "Edible tonnes/year"]}})
        with st.expander("Inspect the calculation and nutrient observations"):
            st.code(f"{exact(demand['kcal_day'])} kcal/day ÷ {exact(obs['value'])} kcal "
                    f"× {exact(food['basis']['amount'])} g = {exact(result['foods'][0]['edible_g_day'])} g/day")
            rows = []
            for nutrient_id, nutrient in result["nutrients"].items():
                value = nutrient["total_day"]
                rows.append({"Nutrient": display_name(catalog["nutrients"][nutrient_id]),
                             "Amount per scenario day": "Unknown — not loaded" if value is None else exact(value),
                             "Unit": nutrient["unit"], "Status": "Incomplete" if value is None else "Reported-data sum"})
            st.table(rows)
            st.caption("These are amounts in the entire calculated scenario mass, not per-person intake or recommended targets.")
        st.download_button("Download food-mass result · JSON", json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False),
                           "human-baseline-food-mass.json", mime="application/json",
                           help="Contains original demand, catalog snapshots, source references, assumptions and missingness.")


if __name__ == "__main__":
    main()
