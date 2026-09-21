# MDL service architecture — 2026-09-21

The user requested four distinct offers and explicitly required offers 01 and 04 to remain separate.

| Offer | Buyer question | Output | Evidence / resources |
|---|---|---|---|
| 01 National mobility program support | How do we plan and deliver the national program locally? | Program plan, stakeholder roles, learning and demonstration delivery, results | TCO Oita FY2025 delivered / FY2026 ongoing |
| 02 Custom app development | Can the workflow fit our users and use case? | UX, prototype, web app and administration screens | Yoko Elevator demonstration |
| 03 Data analysis and database design | Can scattered information support a decision? | Structured data, provenance, maps, analysis interfaces | Two demo themes: accessibility and tourism × transport |
| 04 New venture and co-creation support | Can we develop and test a new business idea? | Customer/business hypotheses, co-creation team, prototype and first validation | Public research: Atlas, Oita events, e-Palette and Shimonoseki proposal |

Separate introduction URLs: `/mobility-support/` and `/venture-support/`. National and other-party examples are research resources, not claimed as MDL client achievements.

## Lightweight Graph review

| Stage | State | Decision / evidence |
|---|---|---|
| Observe | complete | Existing homepage led with 5 needs, 8 reverse steps, 11 activity steps; offers were scattered. |
| Define | complete | Visitors need to identify the purchasable service, deliverable and relevant proof. |
| Decision contract | complete | Site owner requested restructuring; implement and publish in this task, preserve destinations and evidence. |
| Structure | complete | Four offers → scope and outputs → cases or demos → separate contact paths. |
| SIDE+P diagnostic | complete | Clarity and truthful scope are the constraints; published resources must not imply commissioned achievements. |
| Options | complete | Service-led selected; case-led hides deliverables; need-led repeats abstract explanation; no change retains confusion. |
| Refutation | complete | Owner challenged overlap of 01/04; separate pages and buyer objectives. Independent review flagged ambiguous completed/ongoing wording. |
| Execution design | complete | Root homepage, two introduction pages, shared responsive CSS, original cover plus precise live population panel. No new tracking or personal-data collection. |
| Evidence freeze | complete | Existing 35 activities / 750+ cumulative participations retained with owner attribution; FY2026 ongoing, not a completion claim. Population corrected against official records. |
| Audience interface | complete | Local structure/link checks and public Chromium review passed for the homepage and both service pages. Separate entry points, population sources, gallery and demos were exercised. |
| Learning | not executed | No conversion or reader-comprehension effect measured. Technical validation is not evidence of commercial effectiveness. |

Independent first-pass reviews covered service clarity and population evidence. Subsequent review confirmed the scope boundary and required cautious wording for FY2026 activities.

## Cover population

`assets/cases/consortium-cover-original.jpg` preserves the supplied illustration. On the homepage only the title area is displayed. On the introduction page, an accessible HTML/SVG panel replaces the displayed population area; the original image is not offered as the numerical source. The date/footer are project labels rather than a claim of completed exhibition attendance.

Correct values and source locations are in `/mobility-support/population-evidence.json` and in the visible source disclosure. 2000–2020 are census counts; 2030–2040 are IPSS 2023 projections. The 2000→2040 comparison is an MDL calculation, −23.3%, not the original graphic’s −38%.

Continue if visitors can choose 01 or 04 from their purpose and reach the matching case/scope. Revise labels if people confuse program delivery with new-venture discovery. Changes remain reversible in Git.

## Publication verification

Release `d73547645a9aa2b7f9d7eb564393c82c23dbcf4f` passed GitHub Pages build and deployment on 2026-09-21. The public homepage and both introduction pages were reviewed in Chromium.

- At iframe widths 320, 390, 768 and 1440 px (content viewports 305, 375, 753 and 1425 px), all three pages had no horizontal overflow or reported broken images. Desktop and narrow layouts were visually inspected. This is browser width testing, not physical-device testing.
- The population panel fully covers the original incorrect values and shows the corrected census/projection series and −23.3% calculation. The source disclosure opens and contains five data rows with primary-source links.
- The consortium gallery opens and closes its image dialog with the correct caption.
- Homepage links reach the separate 01 and 04 service pages. The accessibility and tourism demo links reach their corresponding live applications.
- Existing `/#yoko-elevator` opens its enclosing catalog disclosure; all 13 news items remain present. Removed heading-only anchors have no incoming references in the repository.
- No inquiry was submitted and no business-conversion outcome is claimed.
