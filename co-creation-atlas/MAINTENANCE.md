# Atlas maintenance record — 2026-10-02

## Canonical release

The public Atlas remains at https://mobilitydlab.com/co-creation-atlas/ in
MDL20241119/MDL20241119.github.io, main branch. Only this directory is changed by
this release. Read the latest remote revision before continuing; do not replace
the 97-case dataset with an earlier 87- or 28-case draft.

## 2026-10-02 addition

Added ten source-backed cases requested for the existing Atlas. Current totals:
97 unique articles, 23 countries, 67 co-creation / 59 place entries (29 shared),
113 photos (109 local and four provider embeds). The original 87 research records
are preserved. New cases carry six human-capital roles, five further input
categories, five concrete value-creation functions mapped to the existing eight
steps, outputs/outcomes, three backcasting mechanisms, a concrete project, and
lens-specific comparisons. Eight steps are not a claim that every case performs
all eight functions.

Independent review checked the material new status, financial, governance and
outcome claims. Source-specific references were corrected for the concrete
project blocks. Jakarta finance is rounded and explicitly 2024; TOD-specific
profit is unverified. Sidewalk is a terminated planning collaboration, not a
completed smart city. Shiojiri budget amounts are estimates, not actual costs.
New image provenance/rights were checked and all local files decoded with
matching dimensions. Four additions use explicitly labelled context photos.

Static build and 126-page local link/anchor checks pass. Desktop public browser
checks are recorded at deployment; local browser execution and localhost preview
are restricted in the cloud environment, so no mobile-device execution is claimed.
No QA-only pages are published. The catalog PDF/images remain the dated 2026-09-28
edition; its web companion identifies this historical count scope.

## 2026-09-28 work consolidated

| Workstream | State in this release |
| --- | --- |
| Original 28 cases and four-part explanations | Retained in the 87-case dataset |
| Two entrances and 59 additional cases | 87 unique article IDs; 62 co-creation / 49 place, with 24 shared |
| Resources and human-capital roles | Six human roles; tangible, relational, financial, intellectual and problem inputs |
| Eight steps | Functions within value creation; not general ordinal maturity labels |
| Reverse design for implementation | Per-case mechanisms plus a consolidated six-question reading guide |
| Learning materials | 21 lessons, a four-part reading guide, workbook and comparison tools |
| Photos | 103 entries covering all 87 cases; 99 local assets and 4 provider embeds |
| References | 515 case-source records, 429 distinct public URLs and one private supplied source |
| Reader annotations | Short photo scope labels and compact source links; longer media details are expandable |

The alternative 28-case renderer is superseded by the current renderer; its
unique reading guide has been adapted into value_guide.py. It is not loaded as
a second case database.

## Verification scope

- Structural: all case IDs, source references, internal page links and anchors,
  four-part sections, image-file existence, decoding and dimensions checked.
- Content: inherited source-based research and independent risk-based reviews;
  important identity, status and numerical claims were sampled. BMW's current
  programme figures and PLATEAU's 329-city figure were additionally matched to
  their primary pages during integration. Full sentence-by-sentence independent
  source verification is not complete.
- Photos: detailed source, attribution, rights and subject metadata retained.
  Local file integrity checked for all 99 assets. Related-district, host-building
  and historical photos are explicitly qualified. Coverage does not mean every
  facility itself or every current activity is pictured.
- External sources and embedded photos may change. A machine retrieval failure
  alone is not evidence that a claim is false.

## Remaining work, in order

1. Complete claim-by-claim source verification, prioritising operational status,
   quantitative outcomes, financial responsibilities and claims of implementation.
   Record KEEP / REVISE / DROP with source locator, date and limits; update the
   public record only when the source supports it.
2. Replace context or historical images with properly attributed facility or
   activity photographs when available. Priority examples: current Garraway F,
   QUINTBRIDGE, Charlotte Innovation Barn, Westside Shed, Kamakura activities,
   Minsta, WISE, Yokohama, Omuta, NEC Shirahama, and GoHubs equipment.
3. Review further historical candidates individually. Historical mention is a
   discovery lead, not publication evidence. Normalise parent organisations,
   campuses, programmes and individual projects before admitting another ID.

## Release gate

### Spatial design feature and photo expansion — 2026-10-27

- `spatial_design.py` adds five pages from the five `data/spatial-design-*.json`
  files. Rebuild with `python3 co-creation-atlas/build.py` from the repository root.
  The feature is independent of the 115-case and 37-frontier datasets.
- The 23 spaces have primary-company counts of 6 / 6 / 6 / 5. McDonald's 2018
  headquarters is counted once and cross-references its joint design roles.
- The 69 photographs in the supplied report remain reference records. Do not
  promote them wholesale into a gallery or imply that separate reuse permission
  has been obtained. Every additional display has its own recorded basis.
- All 23 spaces now display at least three actual photographic views. The feature has 135 regular
  photographs, 24 official video frames, 2 authorized provider photo embeds,
  and 42 specifically analysed photographic quotations. Do not combine these
  into an undifferentiated licensed-photo count. Each video frame has its time code.
  Googleplex historic/event views, Macquarie exterior views, the later T-Mobile
  additions and actual design authorship are explicitly distinguished.
- Newly added CC NC photographs are used only in the free, advertising-free
  learning/analysis feature. They are not promotional materials. NC/ND terms,
  original titles and requested author links are preserved. Publisher editorial
  media terms from PR TIMES, Business Wire and GSK are recorded per item; those
  materials are not generally reusable stock. The GSK JPEG remains unmodified.
- The two CWA photo embeds use the official Behance oEmbed route. Validate the
  exact provider URL and keep its standard aspect ratio and attribution UI.
  Never extract or rehost those covers. Their continued availability depends
  on the provider and the author's embed settings.
- Frasers' two official press-bank photos are recorded as
  `press-editorial-offer-assessed`, with the specific press/download context
  and `explicitLicenseText: false`. This is a limited editorial-use assessment,
  not an assertion of express permission or a reusable stock license.
- Forty-two photos are marked `statutory-quotation`, with at most three
  independently reviewed comparison views per space. This is an editorial
  ceiling, not a statutory safe number. Each has three original analysis
  paragraphs, a distinct `quoteComparisonFocus`, the whole-image necessity,
  author and original source. They are small complete frames, not cropped.
  The index uses one analysed lead image per space; further comparisons stay
  in the article with their own text, source and topic navigation. They are
  excluded from modal sets,
  company covers, OG images and promotional reuse. A quotation is not a claim
  of separate permission; keep its purpose, scope and presentation together.
  The basis was checked against the Agency for Cultural Affairs' 2026 copyright
  text and its legal FAQ 5-13. Changing the purpose requires a fresh assessment.
- The gallery, project index and company jump links show real media counts.
  Modal controls cycle only within one space; captions, author links, original
  titles, dates and license links update with the selected image. Full images
  and original-image links remain available without JavaScript.
- The 41 additional photographs include no new video frames. Duplicate
  source records and perceptual near-duplicates were checked. Kokuyo's two
  shared second-floor lobby views are distinguished from O+A's HQ interior.
  T-Mobile's 2021 renovation photos are distinguished from the 2025 additions.
- `test_spatial_design.py` checks IDs, project references, attribution, image
  sources, exact embed allowlists, quotation boundaries, all-23 visual coverage,
  at least three photographic views per space (video frames cannot fill that
  requirement), comparison topics, direct photo anchors, counts, entry links and sitemap.
  Existing Atlas, Frontier, experts, step-guide and JS checks also passed.
- Chromium iframe viewport checks covered all five new pages at 320, 390, 768,
  1280 and 1440 CSS pixels. No
  horizontal page overflow was found. These are not physical-device tests.
- Photo dialog keyboard/Escape/focus return, URL filter reload/back/forward,
  existing search, mouse and keyboard map switching and a learning step were
  exercised. Existing case/article bodies and four original datasets were
  checked against the starting revision. Repeat build is stable.
- URL retrieval of the 108 supplied references returned 102 successful responses
  and no 404/410 responses. Six remain machine-unverified (timeout, 403, 429 or
  HEAD-not-supported); this is not full claim-by-claim factual validation.
- The user reviewed the implementation summary and authorized the website
  update on 2026-10-27. Publish the checked feature with its assets and verify
  the live feature, photo credits, and existing navigation after deployment.

Run build.py and test_atlas.py, check changed JavaScript, and inspect the public
pages after deployment. Keep changes scoped to this directory, publish without
force, and reconcile any concurrent upstream edit before retrying. Preserve
the distinction between a verified structure and a verified factual claim.

### Photo coverage after expansion

| Space | Gallery media | Official photo embed | Analytical quotation |
| --- | ---: | ---: | ---: |
| kokuyo-hq | 12 | 0 | 0 |
| mcdonalds-innovation-center | 0 | 0 | 3 |
| microsoft-envisioning-center | 0 | 0 | 3 |
| slack-hq | 27 | 0 | 0 |
| uber-old-hq | 1 | 0 | 2 |
| mcdonalds-hq | 17 | 0 | 0 |
| nvidia-campus | 31 | 0 | 0 |
| adobe-founders-tower | 1 | 0 | 2 |
| etsy-brooklyn | 1 | 0 | 3 |
| t-mobile-campus | 4 | 0 | 2 |
| gensler-san-francisco | 1 | 0 | 3 |
| ibm-one-madison | 1 | 0 | 3 |
| tbwa-chiat-day | 5 | 0 | 2 |
| pallotta-teamworks | 0 | 1 | 2 |
| googleplex-2005 | 14 | 0 | 2 |
| macquarie-one-shelley | 3 | 0 | 2 |
| barbarian-group | 14 | 0 | 0 |
| intuit-bayshore | 0 | 1 | 2 |
| google-super-hq | 24 | 0 | 0 |
| frasers-london | 2 | 0 | 3 |
| thg-media-city | 0 | 0 | 3 |
| jojoe-gentilly | 0 | 0 | 3 |
| gsk-global-hq | 1 | 0 | 2 |

## Microsoft Garage photo expansion — 2026-10-27

- The case now contains 22 photographs: 21 News Center editorial additions and the existing CC BY 4.0 exterior. The main corpus now has 162 photographs; the 18 diagrams are unchanged.
- New records in `data/media.json` keep original article/image URLs, original bytes and SHA-256, dimensions, article dates, individual photographer credits, full-frame display, current-status caveats, and the Microsoft Legal permissions URL.
- Microsoft Legal, “Use of Microsoft copyrighted content,” Press section, offers News Center imagery for editorial use by press and industry analysts. This free industry-analysis article follows that context and retains the required permission statement. This is not an unrestricted licence or advertising clearance.
- The selected sources are the 2015 Explorer fabrication story, 2016 MCEC workplace story, 2022 New England Hackathon story, and 2015 3-in-1 Dock story. The nine Vancouver views are labelled as MCEC common/office areas; they are not presented as verified interiors of the dedicated Garage workshop. The Dock views are prototype outcomes, not facility interiors.
- Explicit third-party-copyright-marked candidates (the 2022 winning-team lead and a Red Box Pictures portrait), All Rights Reserved mayoral photos, illustrations, unrelated office/portrait teasers, and duplicate views were not imported.
- The page records GeekWire’s 2026-10-20 report (updated 10-23), which cites an internal FAQ and Microsoft’s spokesperson. It does not assert that every Garage closed at the same time. Original operating-model material is qualified as September 2026 information.
- `photoGroups` is optional case data. When supplied, the builder requires every non-hero photograph to occur in exactly one group. Existing ungrouped cases retain their layout. `publicationNote` appears only for records that supply it.
