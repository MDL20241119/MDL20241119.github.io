# Mobility Design Lab website

Official site: https://mobilitydlab.com/

## Oita mobility atlas

The complete static application is published at `/oita-mobility/`. It includes destinations, municipal transport-gap conditions, local transport resources, timetable planning and conditional analysis. The company homepage links to the tool from NEWS.

All application files and datasets are committed in this repository. GitHub Pages publishes `main` at the root; `.nojekyll` keeps the static output unchanged. No build step or application backend is needed. Do not commit secrets or restricted input data. Background maps are requested from the Geospatial Information Authority of Japan; GitHub Pages hosts the application and its bundled datasets.

The initial transfer preserves the public output of Oita atlas version 7 (source commit `2c9e226d90ed057c6555f7cb8ade44537d1e83c4`) and adds links back to the company site. Public source metadata, analysis qualifications and third-party notices remain in the application. Browser-saved settings from another domain must be exported there and imported here.

## Public demo positioning

The atlas is presented as a public demo, with its existing functionality and datasets unchanged. Each of the four pages displays the demo label and links to a prefilled email to info@mobilitydlab.com for production-development inquiries. Contact addresses are also visible in the footer. No inquiry is sent or stored by the website; visitors send from their email application. The company NEWS describes the tool as a demo.
## Publication and data handling

The visitor-facing [usage and data notice](https://mobilitydlab.com/oita-mobility/usage.html) explains the demo scope, local processing, browser storage, shared URLs, file exports, external map requests and contact handling. New share links omit free-text searches, profile names, notes and custom transport resources. GTFS exports retain source and license information in an accompanying text file.

See [PUBLICATION.md](PUBLICATION.md) for the dated audit and unresolved hosting, survey-law, third-party rights and repository administration checks; [NOTICE.md](oita-mobility/NOTICE.md) for data and software rights; and [SECURITY.md](SECURITY.md) for confidential reporting. A public repository does not automatically grant an open-source license to every file. No blanket MIT or other license has been assigned to MDL code or the corporate-site assets.

Targeted sharing and export checks: `node tests/publication.mjs`. These tests do not certify legal compliance or the absence of every kind of sensitive information.
