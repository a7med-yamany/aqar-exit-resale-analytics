-- Common CTE prepended to each analytics query by repository.py.
-- resale_price excludes transfer/other immediate fees; acquisition_cost includes them.
WITH base AS (
    SELECT l.*, p.area_ID, p.project_ID, p.direct_dev_ID, p.area_sqm,
           p.type AS property_type, p.No_bedrooms, p.No_bathrooms,
           p.location_detail AS property_location,
           CASE WHEN l.remaining_balance IS NOT NULL
                     THEN l.down_payment + l.remaining_balance
                WHEN l.payment_method = 'Cash' THEN l.down_payment
           END AS resale_price,
           CASE WHEN l.remaining_balance IS NOT NULL
                     THEN l.cash_required_now + l.remaining_balance
                WHEN l.payment_method = 'Cash' THEN l.cash_required_now
           END AS acquisition_cost,
           CASE WHEN l.annual_installment IS NOT NULL THEN l.annual_installment
                WHEN l.installment_frequency = 'Monthly' THEN l.installment_amount * 12
                WHEN l.installment_frequency = 'Quarterly' THEN l.installment_amount * 4
                WHEN l.installment_frequency = 'Semi-annual' THEN l.installment_amount * 2
                WHEN l.installment_frequency = 'Annual' THEN l.installment_amount
           END AS annual_installment_normalized
    FROM listing l JOIN property p ON p.property_ID = l.property_ID
), metrics AS (
    SELECT base.*, resale_price / NULLIF(area_sqm, 0) AS resale_price_per_sqm,
           100 * gain_over_current_value / NULLIF(market_price, 0) AS discount_pct,
           CASE WHEN contract_year BETWEEN 1901 AND YEAR(CURDATE())
                THEN YEAR(CURDATE()) - contract_year END AS contract_age_years
    FROM base
)
