# Human Baseline food quantities candidate history

## v0.4.0

User-approved source release, 15 October 2026, based on rc4. Final release
identity and presentation labels; unchanged calculation core, catalog and
population dependency. Small source extracts and illustrative item weights
retain their attribution and limits. Hosted deployment is recorded separately.
Earlier frozen candidates remain unchanged. App 1 is not modified by this release.

## v0.4.0 rc4

Adopts App 1's visual language, metric cards and sidebar About navigation.
Explains the connected layers and links to App 1 with an optional local URL
override. Keeps calculation inputs on the main page. The separate App 1
companion-link UI preparation remains outside this food package. No changed
calculation/data model, public deployment or overwritten earlier candidate.

## v0.4.0 rc3

Adds generic item equivalents in the pure converter, UI and JSON export.
Versioned item assumptions bind label, edible grams per item, food ID/version,
state and provenance. Catalog v0.3 preselects potato and an illustrative,
editable 150 g weight independently for each raw/boiled object; this is not a
measured average. Total and per-person counts cover day, average month and year.
Unknown/zero headcount has no per-person count. Different food units are not
summed. No new food, mixture UI, graph, price or public deployment. rc1 and rc2
remain unchanged.

## v0.4.0 rc2

Adds visible kg/person averages for day, average month and year alongside the
population totals, plus the derived averages in result JSON. Unknown/zero
headcount produces null, not an invented denominator. No individual potato
weight or dietary recommendation is assumed. rc1 remains preserved.

## v0.4.0 rc1

First standalone local candidate for the single-food stage. Direct country,
comparison, EU27 and custom headcount reuse the locked first-layer dependency.
Raw and boiled objects, daily/monthly/annual mass, source data, unknown nutrient
values and JSON exports remain explicit. Population-only online version stays
unchanged. No food-mix controls, price, diet validation or public deployment.

Frozen snapshots are not overwritten. A changed payload requires a new
candidate or later patch version and fresh verification.
