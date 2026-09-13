# 下関、夜のものがたり。 / 関門滞在拠点構想

Public independent concept by Mobility Design Lab. Published 2026-09-13 at https://mobilitydlab.com/shimonoseki-destination/ through the existing repository's GitHub Pages workflow. This is an informational concept, not a booking, sales, tenant recruitment, official redevelopment or transport operating service.

## Scope and evidence

- Daimaru Shimonoseki is currently operating and plans to close on 2027-08-31. The official source is linked on the page.
- No MDL commission, authority to use the property, public endorsement, brand/IP agreement, parking agreement, transport operation or hotel partnership is asserted.
- Existing rail, bus and ferry links are distinct from proposed supplementary transport. No unverified timetable, fare, free parking entitlement, bookable product or late-night return guarantee is published.
- Night economy, greater stays and spending, local income, durable employment and population retention are hypotheses and goals, not measured project results. Local supplier turnover is not summed with wages and downstream turnover to calculate retained income. Shimonoseki, Kitakyushu and Kanmon totals require separate accounting scopes and deduplication.
- Current owner/rights/structural conditions, investment, maintenance costs, demand, operator, payer, permission and procurement route are unresolved. No investment recommendation is made.

## Materials and visitor data

The current edition uses six original AI-generated Naive Zine assets. The existing boat, navigation and food scenes are joined by `assets/history-scenes.webp`, `assets/theatre-scene.webp` and `assets/local-work-scene.webp`. The history image is a four-scene sheet displayed in four CSS viewports; its subjects are conceptual illustrations for the proposed storytelling, not portraits or historical reconstructions. The additional prompts are recorded in `illustration-prompts.json`. They communicate proposed experiences, not actual venue interiors, historical reconstructions or official mascots. The page explains this once in the illustration note. Earlier licensed photographs remain archived in the repository; their metadata is in `photo-credits.json`. They are not displayed in this edition.

The locally hosted Yomogi font is a subset of the official Google Fonts release (https://github.com/google/fonts/tree/main/ofl/yomogi), under the SIL Open Font License in `assets/Yomogi-OFL.txt`. `scripts/subset-font.py` rebuilds the WOFF when supplied the original TTF. Update the subset after adding text.

No third-party character, logo, corporate confidential material, personal operational data or private correspondence is included. The site uses local assets and no analytics, cookies, browser storage, form, location request or external embedded media. GitHub Pages access logging and external-link behavior are explained on the page.

## Illustration-first reading

The four history chapters and three night experiences open with large illustrations and short captions. Creative-experience details and map rationale remain available in native disclosure panels. Map tabs show thumbnails of the actual three diagrams, while all original map panels, course options, sources, caveats and independent keyboard controls remain present. The regional diagrams retain their original precise SVG geometry and responsive variants. A larger community illustration explains who receives local work. `illustrations.css` provides this reading layer over the existing site styles.

## Narrative and night programme

The premise is “日本史が動いた、歴史のまち。” Daytime historical visits give context to a newly written letter, followed by participation at night. Four source-grounded chapters distinguish myth/tradition (Chuai, Jingu and Sumiyoshi), the 1185 Genpei battle, Bakumatsu/Restoration, and the 1895 Treaty of Shimonoseki. Fictional characters and choices do not rewrite historical events. The treaty chapter includes affected communities and the consequences of war; it is not a victory competition. The memorial hall is not described as the surviving 1895 meeting building.

The three proposed experiences are a cooperative Kanmon navigation game, a locally produced participatory food programme, and a small participatory theatre. They are creative proposals, not existing/bookable operations or licensed partnerships. No shrine after-hours use is assumed. Fugu preparation belongs to qualified professional operations; the mock auction changes neither price nor meal entitlement. Professional review, operating conditions and relevant permissions precede any pilot.

Compared with a large permanent attraction, the selected approach starts with small paid food/theatre programmes and portable play equipment. Paid demand, incremental spending/stays, local purchasing, staff conditions and direct operating contribution determine continuation, adaptation or cancellation before permanent investment. Existing night views and dining are acknowledged. No claim is made that Shimonoseki has no night economy or that these programmes alone reverse population loss.

## Decision-quality record

Graph Lite applied to faithful public presentation of the user's concept; no underlying investment approval is implied. A bounded urban/economics review and independent factual verifier were used. Evidence date: 2026-09-13.

| Stage | Status | Remaining condition |
|---|---|---|
| Observe | partial | Public closure/transport facts verified; local demand and costs not measured |
| Define problem | partial | Insufficient reasons and access for overnight stays is a hypothesis |
| Decision contract | partial | Public concept presentation authorized; asset and investment owners not agreed |
| Graph | partial | Stay → spending → local income → jobs → retention is a falsifiable causal hypothesis |
| SIDE+P | partial | Costs, public burdens, fairness and operational responsibilities require investigation |
| Options | partial | Daily-services, destination-experiences, district-circulation and no-development are compared qualitatively |
| Refutation | partial | Displacement, weekday shortfall, capex/opex, transport and community impacts identified |
| Execution design | partial | Investigation → small paid pilot → phased growth; owners and budgets subject to agreement |
| Evidence freeze | blocked | Business-critical building, cost and rights information unverified |
| Audience presentation | complete | Conditional concept and key limitations published consistently |
| Execution/learning | not executed | No business experiment, measured causal impact or operational deployment |

The next decision concerns authorization and resourcing of an investigation, not commitment to redevelopment. Before any pilot, the actual budget owner should fix baseline/comparison days, spending and overnight-stay measures, operator and data owner, complaint handling, loss ceiling, and continue/pivot/stop thresholds. Population retention cannot be attributed to this facility alone.

## Maintenance

Plain static files; no dependency install or build. `app.js` changes three map panels and four illustrative course options, with separate keyboard tab controls. Direct links to `#map-building`, `#map-city`, and `#map-kanmon` select the relevant map. All three maps remain readable without JavaScript. Sources and caveats are rendered in HTML. This edition changes only this special site. Do not overwrite contemporaneous changes to other special sites.

## Three maps and circular mobility concept

- `map-building.svg`: an original exploded floor-stack diagram, with illustrative functions on B1–5F. It is not a measured drawing, current tenant layout, approved design, or inventory of the whole building. Scope for 6F, 7F and roof remains unresolved.
- `map-city.svg`: Shimonoseki Station, Kaikyokan, Karato Market, Akama Shrine, historic Chofu, and Shin-Shimonoseki Station. Double black lines represent existing JR, solid black lines existing buses; the outlined sky-blue dashed circuit is an unoperated proposal. It does not represent surveyed road geometry or approved stops.
- `map-kanmon.svg`: the wider Kokura–Mojiko–Karato–Shimonoseki circuit, with existing JR, bus and ferry connections. Moji Station and Mojiko Station are separate. Transfers, walking links, intermediate stations and operating patterns are simplified.
- Each map has a separate mobile SVG. Text, lines and geometry are original editable SVG, not generated geographical imagery. The generator is `scripts/build-maps.py` (Python standard library only).
- The city loop starts with a proposed weekend pilot. Night journeys are planned around bookings and lodging areas, without claiming a scheduled late-night service. Vehicles, operator, stops, permits, fares, timing, staffing, accessibility and costs require agreement and verification. Booking and ticket integration are unagreed concepts, not live functions.
- Current city bus connections and Chofu access were checked against Sanden Kotsu's official sightseeing access page and Yamaguchi Tourism's Chofu page on 2026-09-13; both are linked on the page. No specific travel-time or frequency promise is made.

Diagram PNGs were rendered with Inkscape to review desktop and mobile label placement; page references, SVG structure, JS syntax and isolated map/course interactions were checked. No browser preview was requested or performed for this update.
