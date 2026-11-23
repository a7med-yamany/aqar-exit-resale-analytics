# Performance improvements and course demonstration

Implemented and measured on 23 November 2026. The application continues using
the remote Aiven MySQL database with certificate and hostname verification.

## What caused the delay

There were separate network, SQL and interface costs:

- A fresh TLS connection took about **0.49-0.61 seconds**, before running a query.
  Previously every uncached read established a new connection.
- The original developer ranking expanded shared-project listings into roughly
  **48,492 developer/listing pairs**, then joined financial data back to those pairs.
- Property-type changes repeated the same full project-ranking query with a
  different cache key, even though the type filter was applied afterwards.
- Every minute the cache expired. Changes inside report tabs could also rebuild
  hidden charts and tables. Listing selection redrew the whole results page.

## SQL optimization: aggregate before expanding joins

The developer query now aggregates listing statistics by project (or standalone
direct developer) first, attributes those smaller groups to developers, and then
combines them. For averages, it carries the sum and non-NULL count:

```sql
SUM(project_price_sum) / NULLIF(SUM(project_price_count), 0)
```

This is a listing-weighted average, preserving the previous result. Averaging the
project averages directly would be wrong when projects have different numbers of
listings. `UNION ALL` is safe because the approved schema makes project and direct
developer attribution mutually exclusive, and `develops` has a unique project/
developer primary key. Listings with unknown developers remain unattributed.

The project-ranking query also groups by project ID and property type before
joining development names. It joins those names only to the final ranked rows,
instead of carrying repeated names through the aggregation.

Head-to-head server execution measurements on the same cloud database and indexes
(median of three `EXPLAIN ANALYZE` executions per version):

| Query | Original | Rewritten | Approx. improvement |
|---|---:|---:|---:|
| Top developers | 1,059 ms | 189 ms | 5.6x |
| Project inventory rankings | 283 ms | 219 ms | 1.3x |
| Project resale-amount rankings | 304 ms | 227 ms | 1.3x |
| Project average-gain rankings | 286 ms | 204 ms | 1.4x |

The original and rewritten results were compared for all three project-ranking
outputs and the developer output. IDs, ordering, counts and labels match; numeric
values match within 0.0001 EGP, below displayed precision. All imported table cells
were separately rechecked against the submitted CSVs.

## Composite indexes applied to Aiven

```sql
CREATE INDEX idx_property_area_type ON property (area_ID, type);
CREATE INDEX idx_listing_year_property ON listing (contract_year, property_ID);
```

The area/type index narrows properties before joining listings in combined
searches. Its leftmost area column can also support an area-only lookup, although
MySQL may prefer the existing smaller area FK index for that case.

The year/property index lets MySQL start from a selective contract year, then join
the matching property. Starting it with year matters: a property-first candidate
was tested but not selected for the target plans. An additional project-covering
candidate also went unused. Both unused candidates were removed; no original
indexes were removed.

For a selective contract search, the final query measured **4.4 ms without the new
indexes versus 0.112 ms with them**, about 39x faster on the server. This was tested
on the same database by excluding only the new indexes through `IGNORE INDEX` in
the baseline query, rather than dropping live indexes. Other queries showed small
or negligible index gains: the broad contract case was 25.4 vs 24.5 ms, the summary
343 vs 343 ms, and the area listing case 29.3 vs 31.5 ms (small timing variation).
An index does not eliminate the work of an aggregate that needs the whole market.

Indexes add storage and maintenance work. We kept only two small nonunique
composite indexes. They do not change source rows, column definitions, primary
keys, foreign keys, unique constraints or check constraints.

## Interface and connection changes

- At most four pooled, exclusively checked-out read connections. Each retains
  verified TLS, autocommit and MySQL read-only transaction mode. Failed/expired
  connections are discarded. Only failed reads may retry once; writes never retry
  automatically and retain their own transaction-owned connections.
- Cached query results last up to **five minutes**, with 128 cache entries maximum.
  **Refresh data** loads current values on demand. Publishing a review invalidates
  that project's review cache immediately; registration no longer clears unrelated
  market reports.
- Rankings cache by metric and filter property type locally. The explorer fetches
  one compact area dataset including amenities, then filters budget, amenities,
  type and year locally. Missing-price behavior and full-area averages are preserved.
- Ranking controls and listing details update their own Streamlit fragments.
  Hidden report tabs do not execute. Downloads do not trigger reruns.

In the read-layer measurements, project statistics/reviews dropped from roughly
**655-710 ms** with fresh connections to **59-62 ms** on a reused connection.
Warm cached datasets returned in **0.2-6.6 ms**. These are backend timings, not
guaranteed browser navigation times; rendering, the first connection, internet
latency and a first uncached query still take time.

## Reproduce and explain in the demo

In Workbench, these read-only statements demonstrate leftmost-prefix/covering
access and selective year lookup:

```sql
USE aqar_exit;
SHOW INDEX FROM property;
SHOW INDEX FROM listing;

EXPLAIN ANALYZE
SELECT property_ID FROM property
WHERE area_ID = 11 AND type = 'شقة';

EXPLAIN ANALYZE
SELECT listing_ID, property_ID FROM listing
WHERE contract_year = 2017;
```

In PowerShell, run `python` from this folder's environment:

```powershell
# Measure plans, index effect and result equivalence. Does not add indexes.
.\.venv\Scripts\python.exe optimize_database.py

# On a fresh import, apply the documented indexes, then measure.
# Safe to repeat: existing matching definitions are retained.
.\.venv\Scripts\python.exe optimize_database.py --apply

# Regression suite, including pool concurrency and schema/index checks.
.\.venv\Scripts\python.exe -m pytest tests -q
```

The checked-in migration is `sql/11_performance_indexes.sql`; use the Python
runner for repeatable application. MySQL DDL commits automatically, so the runner
does not execute inside an application write transaction and uses a short metadata
lock timeout. On a new import without indexes, the schema checker still validates
the original schema. With optimization enabled, it accepts only the two exact
documented additions; a changed definition or missing original constraint fails.

Evidence is in `verification/performance-before.json`, `performance-after.json`,
`query-plans-before.json`, `query-rewrite-comparison.json`, and
`database-optimization.json`. Server load and buffer-cache state affect timings;
the saved reports include raw repetitions and the actual execution trees.

Reference: [MySQL composite indexes](https://dev.mysql.com/doc/refman/8.4/en/multiple-column-indexes.html),
[EXPLAIN](https://dev.mysql.com/doc/refman/8.4/en/using-explain.html),
[avoiding unnecessary indexes](https://dev.mysql.com/doc/refman/8.4/en/optimization-indexes.html),
[Streamlit fragments](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment).
