, project_totals AS (
    SELECT m.project_ID, m.property_type,
           COUNT(*) AS resale_inventory, COUNT(m.resale_price) AS priced_listings,
           SUM(m.resale_price) AS resale_amount,
           COUNT(m.gain_over_current_value) AS gain_known_listings,
           AVG(m.gain_over_current_value) AS avg_gain_over_market,
           SUM(m.gain_over_current_value) AS total_gain_over_market
    FROM metrics m WHERE m.project_ID IS NOT NULL
    GROUP BY m.project_ID, m.property_type
), ranked AS (
    SELECT project_totals.*,
           ROW_NUMBER() OVER (PARTITION BY property_type
               ORDER BY {metric} DESC, project_ID ASC) AS rank_in_type
    FROM project_totals WHERE {metric} IS NOT NULL
)
SELECT ranked.*,d.project_name FROM ranked
JOIN development_project d ON d.project_ID=ranked.project_ID
WHERE rank_in_type <= 10
ORDER BY property_type, rank_in_type
