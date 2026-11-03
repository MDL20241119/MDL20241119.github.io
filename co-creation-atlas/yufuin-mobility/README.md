# Yufuin mobility data story

Published at https://mobilitydlab.com/co-creation-atlas/yufuin-mobility/ .

A standalone static feature within WORLD CO-CREATION ATLAS. No tracking, third-party script dependencies or form submission. Local images and fonts work without third-party content requests.

## Rebuild and check

- `python3 co-creation-atlas/yufuin-mobility/build.py` regenerates the feature HTML and data JSON.
- `python3 co-creation-atlas/mobility_feature.py` idempotently refreshes only the homepage entrance/header and adds this feature to the Atlas sitemap. The full Atlas build also calls it.
- `python3 co-creation-atlas/yufuin-mobility/test_feature.py` checks independent datasets, images, source caveats, links and entry idempotence.
- `node --check co-creation-atlas/yufuin-mobility/app.js`
- The shared Atlas display font is Barlow Condensed Black; its license is in `../assets/display-font-license.txt`. Japanese font subsets derive from Noto Sans CJK JP. Its distribution license is included in `assets/noto-font-license.txt`.

## Editorial boundaries

The three studies are not pooled or treated as a time series. Overall survey counts are not substituted for a missing transport-item denominator. FY2025 Oita data refer to overseas residence, prefecture-wide travel and multiple answers. The material does not establish Yufuin-only charter-bus counts or willingness to use e-Palette.

`data.json` records source URLs, study conditions, values and limitations. `photos.json` records the eight Yufu City photographs, usage terms, original-image hashes, reported image dates and transformations. Dates embedded in source images are not independently verified. Photos illustrate regional scenery rather than current traffic or survey-day conditions.

All animation has reduced-motion support and a manual stop control. Values remain present without JavaScript. Photo dialogs support Escape and restore keyboard focus.
