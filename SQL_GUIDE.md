# SQL requirements and calculation guide

## How the files work

The imported MySQL table names are lowercase; use them exactly on the Linux cloud
server. Keep the existing approved keys, constraints and relationships unchanged.
`repository.py` reads the numbered files in `sql/`. It prepends `00_metrics.sql`
to analytics queries 04-10, so normalized calculations have one definition.
The SQL fragments use PyMySQL `%s` placeholders, not string interpolation.
They are not standalone Workbench scripts: use `run_query.py` to execute them,
or combine the metrics CTE with one report and substitute Workbench variables
when exploring manually. `{metric}` and `{amenity_filter}` are constructed only
from the repository's fixed SQL fragments; user values remain bound parameters.

## Requirement mapping

| Requirement | Python operation | SQL file prefix | Behavior |
|---|---|---|---|
| 1. Register user | `register_user(email, username, gender, birthdate, area_ids)` | 01 | Profile plus one or more focus areas, atomically; email is the existing PK |
| 2. Add project review | `add_review(project_id, email, rating, text)` | 02 | Existing user/project; integer rating 1-10; one review per user/project |
| 3. View project reviews | `project_reviews(project_id)` | 03 | Rating, text and reviewer name; empty list when none exist |
| 4. Top ten projects by property type | `top_projects(metric, property_type=None)` | 04 | Separate inventory, resale-amount and average-gain rankings; at most ten per type |
| 5. Development location and unit-type statistics | `project_statistics(project_id)` | 05 | Stored location, area, listing count and mean resale price/sqm per type |
| 6. Area properties and unit-type averages | `area_properties(area_id)` | 06 | Every listing with its area's unit-type average, using a window function |
| 7. Area, price range and amenities | `search_properties(area_id, min_price, max_price, amenities=())` | 07 | Inclusive resale-price bounds; all selected amenities; empty selection means no amenity restriction |
| 8. Top five developers | `top_developers()` | 08 | Listing-count ranking; mean price/sqm, required down payment, fee-inclusive cash and gain |
| 9. Area, property type, contract year | `contract_properties(area_id, property_type, year)` | 09 | All three filters applied together |
| 10. Area/development market summary | `market_summary()` | 10 | Installments, down payment, property count, discount, contract age and market price |

The read methods return rows as dictionaries; MySQL DECIMAL values remain Python
`Decimal` values. All properties are returned for a requested area; pagination
belongs to the later interface. `lookup_options()` supplies valid IDs and filter
labels. Reports retain stable ID tie-breakers. No saved views or migrations are
needed, and no source financial values are overwritten.

Price bounds in `search_properties` may independently be `None` to omit that bound.
With both bounds omitted, amenity filtering retains matching listings with unknown
prices. The interface uses this when the budget filter is off. Any active price
bound excludes unknown prices. `overview_counts()` and `listing_details(listing_id)`
support the dashboard and property detail view without altering stored data.

## Financial definitions and explicit assumptions

These are implementation defaults because the assignment does not specify every
formula. Their UI labels must remain explicit. All monetary amounts are EGP.

| Metric | Definition |
|---|---|
| Required down payment | Existing `listing.down_payment`: seller amount from the site's primary cash panel, not the original contract's historic down payment |
| Fee-inclusive cash now | Existing `cash_required_now`, shown separately |
| Resale price | `down_payment + remaining_balance`; for explicitly `Cash` listings only, an absent balance means zero; otherwise a missing input produces NULL |
| Acquisition cost including immediate fees | `cash_required_now + remaining_balance`, with the same cash-only missing-balance rule |
| Resale inventory | Number of listings; source currently has one listing per property, but SQL does not assume that forever |
| Resale amount | Sum of known resale prices for a project and property type |
| Resale price/sqm | Resale price divided by positive property area; group mean is the unweighted mean of known listing ratios |
| Gain over market | Stored `gain_over_current_value`; do not recalculate it from seller-only resale price because the source's gain includes immediate fees |
| Project gain ranking | Highest **average known gain amount** within each property type; total gain is also returned for context |
| Discount amount | Stored gain over current market value; negative values remain negative |
| Discount percentage | `100 * gain_over_current_value / market_price`, only with a nonzero known market price |
| Average installment | Average normalized monthly amount, with annual amount also returned; use reported `annual_installment` when present, otherwise annualize Monthly x12, Quarterly x4, Semi-annual x2, Annual x1; unknown frequency stays NULL |
| Contract age | MySQL server's current year minus contract year; missing, zero or future contract years are excluded from the age average |
| Average market price | Mean of known source `market_price` values |

MySQL AVG ignores NULL. All-unknown sums/averages remain NULL, never invented zero.
Relevant coverage counts accompany averages so the interface can show missing-data
coverage. For project rankings, an all-unknown price/gain group is excluded from
that metric's ranking; ties use project ID ascending. Developer ties use developer
ID ascending. Up to ten rows are returned **for each type**, so the complete result
can have more than ten rows.

Project developers come through `develops`. Standalone developers come through
`property.direct_dev_ID` only when no project exists. A UNION creates unique
developer/listing pairs: shared projects count fully for each participating developer,
without multiplying a developer's rows by amenities/images or duplicate joins.
Developer totals across companies therefore need not add up to the market total.

Performance update: developer attribution now aggregates sum/count pairs before
expanding shared projects, preserving listing-weighted means and NULL behavior.
Project rankings group IDs/types before joining project names. The explorer's area
query returns compact listing fields plus an amenities array; full descriptions
remain available from `listing_details()`. Two exact additive performance indexes
are documented in `performance_indexes.json` and `sql/11_performance_indexes.sql`.

Standalone properties appear in area searches and market summaries; a NULL project
ID means an area-level standalone group, not a fabricated development. Project
location can legitimately be NULL. An existing development without listings returns
a row with zero listing count and unknown averages; an unknown project ID returns
no rows. Amenities match the schema's case-sensitive source labels exactly.

## Verification boundaries

Synthetic edge cases run against a disposable MySQL 8.0 instance and the full
import runs against both that instance and Aiven MySQL 8.4. Remote write checks
always roll back; actual commit/read-from-another-connection behavior is tested
only in the disposable instance. The Market Studio interface now uses this SQL
layer. No public deployment or authentication system has been added. Source rows
and original constraints are unchanged. The two
performance indexes are the only live schema additions.
