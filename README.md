# Mobility Design Lab website

Official site: https://mobilitydlab.com/

## Corporate homepage — 2026-09-21

The homepage is authored in `index.html`, `assets/home.css`, and `assets/home.js`.
It introduces MDL as a company that implements services in society, starting
from the desired outcome and working back to the customer's current obstacles.
The design uses PaperWhite, black rules and one Neo Swiss accent per section.

- `/mobility-training/`: all 61 official FY2025 adopted projects, backed by JSON.
  `data/manifest.json` permits additional fiscal years. Keep unknown, planned,
  implemented, and unrelated/other-year sources separate. No ranking or score.
- `/evidence/`: 35 activity records, participant and pilot metric definitions.
  750+ is MDL's 2026-09-21 reported aggregate; detailed reconciliation is pending.
- `/danchi-elevator/`: the implementation tool, prices, role demos and catalogs.
- `/danchi-elevator/standards/`: public compliance matrix, source and test evidence.
- `integrations/yoko/`: original application plus audited adapter corrections,
  for local synthetic-data testing. GitHub Pages does not run this API server.

Validation:

```sh
python3 scripts/check-mdl-release.py
node tests/training-database.test.mjs
node --check assets/home.js
```

`tests/mdl-responsive.html` checks the five pages in 320/390/768/1440px iframes.
It is not a real-device, Safari, GPS or external-service interoperability test.
Application test instructions are in `integrations/yoko/README.md`.
Preserve existing catalogs, application URLs, news archive, pricing scope and
demo qualifications. Do not call test success government certification or
complete production conformance.

## Oita mobility atlas

### Shopping and route maps — 2026-09-22

- 321 destinations, including 145 shopping locations across 16 municipalities
  (71 supermarkets/food stores, 73 drugstores, one home centre). Source URLs,
  addresses, source map coordinates, position qualifications and check dates are
  retained in `access/shopping-sources.json`; rebuild with
  `node scripts/build-shopping-destinations.mjs`.
- PEOPLE shows searchable, paginated destination cards, shop types and proximity
  order. The map supports selecting/switching endpoints and round-trip searches.
- Bus geometry follows the selected GTFS trip and is clipped to the actual
  boarding/alighting calls, including loop direction. Pink is outbound, blue is
  inbound. Walking remains an explicitly approximate dotted line. Missing or
  inconsistent bus shapes show boarding/alighting points without an invented line.
- These are published scheduled routes, not a GPS trace or a road-navigation API.

Checks: `node --test tests/route-map.test.mjs tests/route-shapes-real.test.mjs` and
`node scripts/build-shopping-destinations.mjs --check`.

### Atlas 2.0 — 2026-09-22

- `/oita-mobility/`: PEOPLE starts with current location or one of 18 municipalities.
  The selected area reveals its map above the origin, destination and time form; an
  explicit checkbox includes destinations in other municipalities. City selection
  passes to ATLAS as a coarse municipality code. PEOPLE finds timetable-based round-trip candidates using
  origin, destination, activity time, dwell time and return deadline. Walking
  and transfers reuse the existing accessibility engine. Thirty/sixty-minute
  opportunity counts distinguish missing evidence from zero candidates.
- `/oita-mobility/atlas.html`: ATLAS compares populated 1km representative
  points under one explicit facility/time/profile. The denominator is the
  bundled 2020 population with known values, including unknown-access cells;
  these figures are not actual passengers or confirmed mobility deprivation.
- `/oita-mobility/policy.html`: LAB inherits the baseline in sessionStorage,
  recalculates bus changes, and labels other interventions as user assumptions.
  Unknown-before/after cells do not count as measured population gains. Cost
  per net candidate person-year is absent for missing costs or nonpositive gains.
- `/oita-mobility/analysis.html` retains the previous analysis homepage. Older
  map/ridership/cost anchors redirect here. Existing detailed tools stay available.

The new worker admits only GTFS feeds with known validity for the selected day.
Excluded/expired feeds remain in result evidence. Timetable candidates are not
confirmed journeys: fares, real-time disruptions, rail, facility acceptance,
walking routes, vehicle capacity and unknown accessibility need confirmation.
No invented live location, price or guaranteed last-return time is displayed.

Demand records are optional and device-local, capped at 5,000. Search records
and self-reported outcomes are separate; coordinates, facility names, exact
dates, identities and free text are never stored in these records. Shared CSV
aggregates require at least five identical records. This is not a prefecture-wide
collection backend or a legal anonymity guarantee. See `usage.html`.

Targeted regression checks:

```sh
node --test tests/atlas-v2.test.mjs tests/accessibility.test.mjs tests/planning.test.mjs tests/gaps.test.mjs
```

`tests/atlas-v2-responsive.html` is a noindex iframe harness for 320/390/768/1440
CSS-pixel layouts. It does not claim real-device Safari, GPS or live-operations validation.

The complete static application is published at `/oita-mobility/`. It includes destinations, municipal transport-gap conditions, local transport resources, timetable planning and conditional analysis. The company homepage links to the tool from NEWS.

All application files and datasets are committed in this repository. GitHub Pages publishes `main` at the root; `.nojekyll` keeps the static output unchanged. No build step or application backend is needed. Do not commit secrets or restricted input data. Background maps are requested from the Geospatial Information Authority of Japan; GitHub Pages hosts the application and its bundled datasets.

The initial transfer preserves the public output of Oita atlas version 7 (source commit `2c9e226d90ed057c6555f7cb8ade44537d1e83c4`) and adds links back to the company site. Public source metadata, analysis qualifications and third-party notices remain in the application. Browser-saved settings from another domain must be exported there and imported here.

## Neo Swiss design

The atlas now carries the Neo Swiss design published in Sites version 8 (source `5871c5c826ac9271a7b8540567954d6e96236aac`). A shared `oita-mobility/assets/neo-swiss.css` theme supplies paper-white surfaces, ruled grids, large collection counts and cyan/pink/yellow tool accents across all five pages. Mobile entry cards and map controls use the same hierarchy. The directory counts describe the current bundled coverage: 321 destinations, 18 municipalities, 15 transport-resource examples and 16 public GTFS files.

GitHub Pages links, contact URLs, privacy disclosures and storage-domain instructions remain specific to `mobilitydlab.com/oita-mobility/`. The existing analytical engines, data, sharing safeguards and source notices are retained. Validation covers local page references, existing element IDs, identical stylesheet delivery and `node tests/publication.mjs`.

## Public demo positioning

The atlas is presented as a public demo, with its existing functionality and datasets unchanged. Each of the four pages displays the demo label and links to a prefilled email to info@mobilitydlab.com for production-development inquiries. Contact addresses are also visible in the footer. No inquiry is sent or stored by the website; visitors send from their email application. The company NEWS describes the tool as a demo.
## Publication and data handling

The visitor-facing [usage and data notice](https://mobilitydlab.com/oita-mobility/usage.html) explains the demo scope, local processing, browser storage, shared URLs, file exports, external map requests and contact handling. New share links omit free-text searches, profile names, notes and custom transport resources. GTFS exports retain source and license information in an accompanying text file.

See [PUBLICATION.md](PUBLICATION.md) for the dated audit and unresolved hosting, survey-law, third-party rights and repository administration checks; [NOTICE.md](oita-mobility/NOTICE.md) for data and software rights; and [SECURITY.md](SECURITY.md) for confidential reporting. A public repository does not automatically grant an open-source license to every file. No blanket MIT or other license has been assigned to MDL code or the corporate-site assets.

Targeted sharing and export checks: `node tests/publication.mjs`. These tests do not certify legal compliance or the absence of every kind of sensitive information.


## DATA CATALOG (2026-09-10)

`/oita-mobility/data-catalog.html` adds the source catalog, layer map, municipal data-coverage matrix, and recorded acquisition history. Existing page URLs, raw datasets, numerical analysis engines and Scenario Lab remain intact.

- `oita-mobility/data/catalog.json` is generated metadata. **Do not edit it by hand.**
- Rebuild after changing source files: `python scripts/build-data-catalog.py` (Python standard library, no external API).
- Verify reproducibility: `python scripts/build-data-catalog.py --check`.
- Verify provenance, date separation, real GTFS worker and result semantics: `node tests/data-catalog.mjs`.
- Verify established mathematics: `node --test tests/planning.test.mjs tests/accessibility.test.mjs tests/gaps.test.mjs`.
- Verify export attribution/privacy: `node tests/publication.mjs`.
- `/tests/responsive.html` is a noindex manual QA harness for the same public pages at 320/390/768/1440 CSS pixels. It does not emulate device-specific browser behavior.

The catalog records hashes of all input GIS/GTFS JSON and ZIP files. Dataset units are declared (feed, source collection, reported table, or derived calculation). Counts are computed from records rather than authored in the UI. Planned entries are excluded from overview dataset counts. Baseline, acquisition, source update, webpage check, validity period and calculation dates are separate fields; one never substitutes for another.

The matrix measures **this site's data collection**, not transport availability. A cross means uncollected. Existing non-empty but non-comprehensive collections remain PARTIAL; there is no invented completeness, verification or partner agreement. Resource coordinates denote published facilities/pickup references, never available vehicles or service-area coverage. Population is the bundled 2020 adjusted baseline; no older-population or future figures are substituted.

ACCESSIBILITY retains its routing mathematics and adds result provenance and four presentation states. Missing/incomplete/expired inputs do not become confirmed absence. Known user-supplied service eligibility rejections retain their explicit reason. Original engine states remain available for compatibility. DATA USED uses the calculation's actual feed hashes and facility IDs; the display falls back gracefully if the catalog cannot load.
