-- Aggregate once before expanding developer attribution; use weighted sum/count means.
, attribution_totals AS (
    SELECT project_ID,direct_dev_ID,COUNT(*) AS n,
           COUNT(resale_price_per_sqm) AS price_n,SUM(resale_price_per_sqm) AS price_sum,
           COUNT(down_payment) AS down_n,SUM(down_payment) AS down_sum,
           COUNT(cash_required_now) AS cash_n,SUM(cash_required_now) AS cash_sum,
           COUNT(gain_over_current_value) AS gain_n,SUM(gain_over_current_value) AS gain_sum
    FROM metrics GROUP BY project_ID,direct_dev_ID
), developer_groups AS (
    SELECT dp.dev_ID,t.n,t.price_n,t.price_sum,t.down_n,t.down_sum,
           t.cash_n,t.cash_sum,t.gain_n,t.gain_sum
    FROM attribution_totals t JOIN develops dp ON dp.project_ID=t.project_ID
    UNION ALL
    SELECT t.direct_dev_ID,t.n,t.price_n,t.price_sum,t.down_n,t.down_sum,
           t.cash_n,t.cash_sum,t.gain_n,t.gain_sum
    FROM attribution_totals t
    WHERE t.project_ID IS NULL AND t.direct_dev_ID IS NOT NULL
), developer_totals AS (
    SELECT dev_ID,CAST(SUM(n) AS UNSIGNED) AS listing_count,
           CAST(SUM(price_n) AS UNSIGNED) AS priced_listings,
           SUM(price_sum)/NULLIF(SUM(price_n),0) AS avg_price_per_sqm,
           SUM(down_sum)/NULLIF(SUM(down_n),0) AS avg_required_down_payment,
           SUM(cash_sum)/NULLIF(SUM(cash_n),0) AS avg_cash_required_now,
           SUM(gain_sum)/NULLIF(SUM(gain_n),0) AS avg_gain_over_market,
           SUM(gain_sum) AS total_gain_over_market
    FROM developer_groups GROUP BY dev_ID
)
SELECT t.*,d.dev_name FROM developer_totals t
JOIN developer d ON d.dev_ID=t.dev_ID
ORDER BY listing_count DESC,t.dev_ID ASC LIMIT 5
