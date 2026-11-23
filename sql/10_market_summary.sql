SELECT m.area_ID, a.area_name, m.project_ID, d.project_name,
       COUNT(DISTINCT m.property_ID) AS property_count,
       COUNT(*) AS listing_count,
       AVG(m.resale_price) AS avg_resale_price,
       AVG(m.resale_price_per_sqm) AS avg_price_per_sqm,
       AVG(m.annual_installment_normalized / 12) AS avg_monthly_installment,
       AVG(m.annual_installment_normalized) AS avg_annual_installment,
       COUNT(m.annual_installment_normalized) AS installment_known_listings,
       AVG(m.down_payment) AS avg_down_payment,
       COUNT(m.down_payment) AS down_payment_known_listings,
       AVG(m.cash_required_now) AS avg_cash_required_now,
       AVG(m.gain_over_current_value) AS avg_discount_amount,
       AVG(m.discount_pct) AS avg_discount_pct,
       COUNT(m.gain_over_current_value) AS discount_known_listings,
       COUNT(m.discount_pct) AS discount_pct_known_listings,
       AVG(m.contract_age_years) AS avg_contract_age_years,
       COUNT(m.contract_age_years) AS contract_age_known_listings,
       AVG(m.market_price) AS avg_market_price,
       COUNT(m.market_price) AS market_price_known_listings
FROM metrics m JOIN area a ON a.area_ID = m.area_ID
LEFT JOIN development_project d ON d.project_ID = m.project_ID
GROUP BY m.area_ID, a.area_name, m.project_ID, d.project_name
ORDER BY m.area_ID, m.project_ID
