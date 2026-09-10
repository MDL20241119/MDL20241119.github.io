# Mobility Design Lab website

Official site: https://mobilitydlab.com/

## Oita mobility atlas

The complete static application is published at `/oita-mobility/`. It includes destinations, municipal transport-gap conditions, local transport resources, timetable planning and conditional analysis. The company homepage links to the tool from NEWS.

All application files and datasets are committed in this repository. GitHub Pages publishes `main` at the root; `.nojekyll` keeps the static output unchanged. No build step or application backend is needed. Do not commit secrets or restricted input data. Background maps are requested from the Geospatial Information Authority of Japan; GitHub Pages hosts the application and its bundled datasets.

The initial transfer preserves the public output of Oita atlas version 7 (source commit `2c9e226d90ed057c6555f7cb8ade44537d1e83c4`) and adds links back to the company site. Public source metadata, analysis qualifications and third-party notices remain in the application. Browser-saved settings from another domain must be exported there and imported here.

## Neo Swiss design

The atlas now carries the Neo Swiss design published in Sites version 8 (source `5871c5c826ac9271a7b8540567954d6e96236aac`). A shared `oita-mobility/assets/neo-swiss.css` theme supplies paper-white surfaces, ruled grids, large collection counts and cyan/pink/yellow tool accents across all five pages. Mobile entry cards and map controls use the same hierarchy. The directory counts describe the current bundled coverage: 199 destinations, 18 municipalities, 15 transport-resource examples and 16 public GTFS files.

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
