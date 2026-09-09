# Mobility Design Lab website

Official site: https://mobilitydlab.com/

## Oita mobility atlas

The complete static application is published at `/oita-mobility/`. It includes destinations, municipal transport-gap conditions, local transport resources, timetable planning and conditional analysis. The company homepage links to the tool from NEWS.

All application files and datasets are committed in this repository. GitHub Pages publishes `main` at the root; `.nojekyll` keeps the static output unchanged. No build step, backend, secret, or external source hosting is needed.

The initial transfer preserves the public output of Oita atlas version 7 (source commit `2c9e226d90ed057c6555f7cb8ade44537d1e83c4`) and adds links back to the company site. Public source metadata, analysis qualifications and third-party notices remain in the application. Browser-saved settings from another domain must be exported there and imported here.
