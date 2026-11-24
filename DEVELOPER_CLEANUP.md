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

Final counts: developers **2,328 -> 2,324**; project/developer links **3,254 ->
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
