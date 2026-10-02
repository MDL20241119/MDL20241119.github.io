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

Run build.py and test_atlas.py, check changed JavaScript, and inspect the public
pages after deployment. Keep changes scoped to this directory, publish without
force, and reconcile any concurrent upstream edit before retrying. Preserve
the distinction between a verified structure and a verified factual claim.
