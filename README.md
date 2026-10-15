# Human Baseline · Food quantities v0.4.0

This is the standalone v0.4.0 source release: choose a population and daily kcal
figure, then inspect the energy-equivalent mass of one catalog food. It uses
the preserved first-layer calculation and the fixed EU27 population capture.
Raw and boiled potatoes are separate sourced objects. Daily, average-month
and annual mass are shown for the whole population and as kg/person averages.
Zero/unknown headcount has no per-person average. Approximate item counts are
also shown for day, average month and year, total and per person. Potato objects
preselect the label potato and an editable illustrative 150 g edible weight.
This is a scenario assumption, not a measured average or DTU item-size data.
Raw and boiled weights are separate assumptions, not a cooking yield. Each
assumption and its provenance travel with the exported result; other food
objects need their own item data or explicit input. Fractional equivalents
are not rounded purchase quantities.
This is not a complete
diet, purchased-weight, price or food-production model. Interface: English.

The presentation follows App 1: pale background, Georgia heading and metric
typography, bordered metric cards, main-page inputs and sidebar About & sources.
The explanation describes the two layers and links to the published population
tool. `HB_POPULATION_APP_URL` optionally overrides that link for local paired
previews. Its default is the existing public App 1 URL, not localhost.
App 1's separate local About update uses `HB_FOOD_APP_URL` for its backlink;
that companion UI update is not bundled here and has not been deployed. Set
its actual public target only after the food app has an assigned public URL.

## Run from this directory

Use Python 3.12 and an isolated virtual environment. Install the requirements
with their included constraints, then verify the package and run the tests:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
.venv/bin/python verify_release.py
.venv/bin/python -m unittest discover -p 'test_*.py' -v
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8798
```

`_vendor/population/` contains generated, unchanged copies of the original
population model, calculation core and data. `dependency-lock.json` pins their
hashes and source commit; the adapter checks those hashes before loading them.
Change the canonical owner and create a new candidate, not the generated copy.
`release-manifest.json` lists the exact payload; a preparation timestamp is not
a public release date.

## Streamlit deployment

The exact payload was approved for a dedicated public food-project repository
and a separate Streamlit app on 15 October 2026. Hosting branch:
`release/v0.4.0`. Entrypoint:
`app.py`; Python 3.12; no secrets required. Record the actual assigned URL and
verify country/comparison/EU27/custom calculations, both food objects,
downloads and mobile behavior on the hosted runtime.

Do not deploy this over the existing population-only app. A source release is
not proof of deployment: the actual assigned app URL, deployment time and
hosted feature readback are recorded separately after hosting. No secrets are
required. Earlier candidate snapshots remain unchanged.

## Sources and limits

See `SOURCE-NOTICES.md`. Input choices, source captures and original demand
are included in exported result JSON. Nutrient missingness remains visible.
The amount of cooked food does not establish raw input, harvest or purchased
weight. No energy-share UI or new functional layer is included in this version.
