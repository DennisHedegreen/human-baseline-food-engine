# Human Baseline candidate source notices

## Population and calculation dependency

Eurostat DEMO_PJAN, population on 1 January 2025 by age and sex, captured
5 October 2026. The fixed 27-country data files are the same bytes used in the
public first-layer snapshot v0.3.0-rc2. Source:
https://ec.europa.eu/eurostat/databrowser/view/demo_pjan/default/table

Country selection, adaptation and calculations are by Hedegreen Research.
Eurostat is not responsible for the adaptation or its results. Reuse policy:
https://ec.europa.eu/eurostat/help/copyright-notice

The dependency is pinned to public repository commit
`edbd253b6908e1c8cc6e210e262265cda10eec98`; generated copies are hash-checked
against its previously verified snapshot. No NNR, WHO, infant or maternal
reference tables are included in this candidate.

## Food observations

DTU National Food Institute, current public records:

- Raw unspecified potato, record 4, captured 13 October 2026:
  https://fcdb.fooddata.dk/food/11/4
- Boiled potato, record 801, captured 14 October 2026:
  https://fcdb.fooddata.dk/food/11/801

The catalog includes a small, attributed numeric extract per 100 g, not the
whole database. The original manual extraction notes accompany the package.
Database release number is unverified; URL segment 11 is not used as a release
identifier. Unloaded Vitamin C remains null; the nutrient table is not complete.
The 150 g per-item defaults are editable calculator examples, not DTU
observations or measured potato averages.

DTU's introduction explains representative market averages and the per-100-g
table basis. Its disclaimer gives no accuracy/completeness guarantee and
disclaims responsibility for subsequent use including software. These reviewed
pages do not themselves state an explicit blanket redistribution licence. This
is not a finding that numerical use is prohibited. The exact small payload and
its source limitations were reviewed on 15 October 2026 and included in the
user's release decision. No whole-database redistribution clearance is claimed.

https://fcdb.fooddata.dk/introduction
https://fcdb.fooddata.dk/disclaimer

Raw and cooked records are not a paired yield experiment. No cooking loss,
peeling factor, purchased-weight conversion, price or diet approval is inferred.
