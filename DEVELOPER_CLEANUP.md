# Talaat Moustafa Group identity cleanup

## Approved scope

On 24 November 2026, Ahmed explicitly confirmed that developer IDs **5, 13, 33 and
38** represent the same developer and requested the English name **Talaat Moustafa
Group**. Ahmed subsequently confirmed inclusion of **ID 18**, a spelling variant
exposed by the refreshed ranking. These are explicit identity decisions, not fuzzy
matching. Exact names and authority are recorded in `developer_merge.json` and
`developer_merge_additional.json`.

Existing ID **38** is retained. IDs 5, 13, 33 and 18 are redirected through all incoming
foreign keys before their duplicate developer records are removed. No other developer
identities, project names, listing values, or financial definitions are changed.

## Why listing counts must not be added

Before cleanup, the four IDs have **58 project/developer associations**, covering
only **25 distinct projects**. Their listing sets overlap. Summing the four ranking
rows would count listings repeatedly. The correct union is **893 listings**.

The migration preserves each project association once, adding eight missing links
to ID 38 and removing 41 alias links: a net reduction of **33 duplicate links**.
The separately approved ID 18 adds five more duplicate project links, all already
covered by the canonical developer. Removing those leaves the union unchanged:
**25 projects and 893 listings**, with **38 duplicate links removed in total**.
The schema currently has no direct property references to these aliases; that FK
is nevertheless handled and covered by integration tests. A schema check prohibits
direct developer IDs on properties that already belong to a project.

After the first two stages: developers **2,328 -> 2,324**; project/developer links **3,254 ->
3,216**. Properties remain **8,772**, listings remain **8,772**, and all genuine
profiles, focus areas and reviews are preserved. Other developers retain their own
listing attribution even when they share a project with TMG.

## Safety and evidence

- Milestone 2 files remain unchanged; their dump, submission ZIP and 13 CSVs have
  recorded SHA-256 hashes in the pre-merge backup manifest.
- Full current Aiven backups are under `backups/`, including genuine website writes
  since Milestone 2. These are private and excluded from GitHub uploads.
- `clean_developers.py --rehearse BACKUP_FOLDER` restores the backup into disposable
  local MySQL, compares all stored cells and schema, tests a merge, checks the exact
  expected transformation, exports cleaned CSVs/SQL, restores that SQL again, and
  reruns report/foreign-key/write-rollback checks.
- `clean_developers.py --apply` requires a passed rehearsal of the exact migration
  source hashes, takes another live backup, uses an explicit transaction/savepoint,
  validates before commit, and updates only affected records. It does not import
  a stale database over current website writes or disable FK checks.
- For the separately approved follow-up, add
  `--manifest developer_merge_additional.json` to rehearsal/apply commands.
  Each manifest is applied separately; rerunning a completed stage is a no-op.
- Unexpected IDs, names, references or schema changes cause failure/rollback.
  Repeating the migration on the canonical state is a no-op.
- Post-commit exports are staged privately, using a single cloud SQL snapshot for
  the dump and all CSVs. Its local restore and exhaustive verification must pass
  before the staging directory becomes `dataset/current`. A failed export does not
  publish a partial baseline; a retry can export again. Prior releases are retained.
- Evidence: `verification/developer-merge-rehearsal.json`,
  `verification/developer-merge-tests.xml`, `verification/developer-merge-live.json`.
  The live report distinguishes pre-commit validation, committed/export-pending,
  and completely verified states.
- `verification/developer-merge-first-*.json/xml` preserve the completed original
  four-record stage; the main reports describe the separately approved ID 18 stage.

## Current Milestone 3 artifacts

After successful application:

- `dataset/current/csv/`: all 13 tables, including current website profiles/reviews.
- `dataset/current/sql/aqar_exit_milestone3_cleaned.sql`: full populated MySQL dump,
  including both performance indexes and all original constraints.
- `dataset/current/manifest.json`: export hashes, counts and validation status.
- `dataset/candidate*/`: locally rehearsed candidates retained as evidence.

`verify.py` prefers `dataset/current/csv` when present. To verify an original
Milestone 2 import, explicitly pass `--baseline ../milestone_2_submission/csv`.
Verification compares an exported snapshot: later genuine website writes can make
user-related tables differ. Refresh the export before final submission; do not
overwrite new records to force an old baseline match.

The hosted and local apps read Aiven and need no developer-specific query patch.
Use **Refresh data**, or wait up to five minutes, to discard cached rankings.

## Recovery

Do not restore a full backup over an active database without accounting for newer
website writes. To reverse this narrow merge, inspect the saved pre-merge backup
in a separate database and restore its alias developer rows and original
project/developer links in a reviewed transaction. Preserve links added since the
migration. The decision manifest preserves the exact old identities. Milestone 2
remains the original submission backup and is not rewritten by this cleanup.

Other unconfirmed developer aliases may remain. This cleanup makes no claim that
all developer identities in the source dataset have been resolved.

## Further confirmed English spelling and sidebar refinement

The subsequent user report explicitly confirms **Talaat Mostafa** as the same
developer. `developer_merge_spelling.json` records ID **597** and its case-only
duplicate **1982**, plus **2492**, which adds only an Arabic vowel mark to the
previously confirmed Arabic name. An audit of all developer names against the
already confirmed spellings identified these exact typography variants; no fuzzy
or semantic identity inference is used. Their nine project links add one project
to the canonical union; eight duplicate links collapse. The canonical developer
has **26 projects and 894 distinct listings**. All seven removed alias IDs are
**5, 13, 18, 33, 597, 1982, 2492**, retained in three decision manifests.

After this follow-up the developer count is **2,321** and the project/developer
link count is **3,208** (46 redundant links removed across all three stages).
The original stage counts above remain as historical evidence. The ID 18 stage
reports are preserved as `verification/developer-merge-id18-*`; the main merge
reports now track the latest spelling stage. Use
`--manifest developer_merge_spelling.json` to rehearse/apply this stage.

The sidebar's empty pair of horizontal lines came from Streamlit's native
navigation separator plus the custom `.studio-side-note` border. The redundant
custom border and its excessive top spacing are removed; the native separator
continues to divide navigation from the market information and refresh controls.

### Decision to stop further cleaning

After Aser replied that extra data cleaning is unnecessary, Ahmed instructed us
to retain the current state and stop further cleaning. The applied state remains
**2,321 developers**, **3,208 developer/project links**, and canonical TMG **894
listings across 26 projects**. Milestone 2 remains unchanged.

Seven additional transliteration/company-prefix candidates were rehearsed but
**not applied**. Their proposal is archived locally at
`developer_review/deferred_transliterations.json` with status `deferred_do_not_apply`;
the associated rehearsal is marked `deferred_not_applied`. No further identity
merges are planned. Additional uncertain names remain in `developer_identity_review.csv`.

The latest completed spelling stage passed all 13-table cloud cell comparisons,
strict schema checks, all 17 FK checks, and temporary write/rollback probes. The
sidebar fix is published and browser-verified: one native separator, no custom
note border or empty extra top spacing.

## Verification of the first two stages (24 November 2026)

Both approved migrations and post-commit dump restores passed. The final independent
Aiven verification matched every stored cell against all 13 current CSVs, checked
all 17 FK relations and the strict schema including both performance indexes, and
verified temporary registration/review writes with rollback. All **49 automated
tests** passed; all **six interface pages** rendered with the cleaned live backend.
The 15 protected Milestone 2 artifact hashes remain unchanged.

Final snapshot: **88,246 rows**, including **602 profiles**, **1,004 reviews** and
**1,503 focus-area links**. None of those genuine website records were removed.
Summary evidence: `verification/developer-cleanup-summary.json` and
`verification/developer-merge-final-remote-console.json`.
