# Yufuin mobility data story

Published at https://mobilitydlab.com/co-creation-atlas/yufuin-mobility/ .

A standalone static feature linked from the MDL homepage data-analysis section, retaining its original URL. No tracking, third-party script dependencies or form submission. Local images and fonts work without third-party content requests.

## Rebuild and check

- `python3 co-creation-atlas/yufuin-mobility/build.py` regenerates the feature HTML and data JSON.
- `python3 co-creation-atlas/yufuin-mobility/test_feature.py` checks independent datasets, images, source caveats, links, independent percentage rings, historical bus evidence and the MDL homepage entry.
- `node --check co-creation-atlas/yufuin-mobility/app.js`
- The shared Atlas display font is Barlow Condensed Black; its license is in `../assets/display-font-license.txt`. Japanese font subsets derive from Noto Sans CJK JP. Its distribution license is included in `assets/noto-font-license.txt`.

## Editorial boundaries

The three studies are not pooled or treated as a time series. Overall survey counts are not substituted for a missing transport-item denominator. FY2025 Oita data refer to overseas residence, prefecture-wide travel and multiple answers. The material does not establish Yufuin-only charter-bus counts or willingness to use e-Palette.

`data.json` records source URLs, study conditions, values and limitations. `photos.json` records the eight Yufu City photographs, usage terms, original-image hashes, reported image dates and transformations. Dates embedded in source images are not independently verified. Photos illustrate regional scenery rather than current traffic or survey-day conditions.

All animation has reduced-motion support and a manual stop control. Values remain present without JavaScript. Photo dialogs support Escape and restore keyboard focus.

## November 3 revision

The entry moved from Atlas to the MDL homepage's data-analysis section. Only the previously added Atlas entrance, menu item and insertion helper were removed. The feature URL is unchanged.

Neither the 2022 summer paper nor the city plan establishes exclusive single-answer transport shares in the accessible sources. Their percentages therefore use separate 100%-scale rings, not one composition pie. Grey is scale remainder, not an inferred transport category. The prefecture's multiple-answer chart remains separate and is not normalized.

Historical bus evidence distinguishes: 60–100 parked tourist buses per day reported in the June 2017 council meeting; approximately 100 buses entering the centre daily in a 2017 proposal reproduced in the March 2018 tourism plan; and approximately 480,000 annual users of the Yufuin-go highway route in FY2017. These are not current measurements and must not be summed.

## November 4 field research

The build reads `downloads/Yufuin-Field-Evidence.json` (56 source records, monthly lodging and transport connections) and `downloads/Yufuin-Nolc-OD-2020.json` (directional boardings in the 2020 trial). Dedicated Python renderers generate the sections. Run the same offline checks after rebuilding. The first three routes for Yufuin Station, the monthly values, and all source notes are available without JavaScript.
