SELECT m.listing_ID,m.property_ID,m.area_ID,m.project_ID,m.property_type,
       m.area_sqm,m.No_bedrooms,m.No_bathrooms,m.contract_year,
       m.resale_price,m.resale_price_per_sqm,m.down_payment,m.cash_required_now,
       m.remaining_balance,m.market_price,m.gain_over_current_value,
       a.area_name, d.project_name,
       (SELECT JSON_ARRAYAGG(pa.amenities) FROM propertyamenity pa
        WHERE pa.property_ID=m.property_ID) AS amenities_json,
       AVG(m.resale_price_per_sqm) OVER (PARTITION BY m.area_ID, m.property_type)
           AS area_type_avg_price_per_sqm,
       COUNT(m.resale_price_per_sqm) OVER (PARTITION BY m.area_ID, m.property_type)
           AS area_type_priced_listings
FROM metrics m JOIN area a ON a.area_ID = m.area_ID
LEFT JOIN development_project d ON d.project_ID = m.project_ID
WHERE m.area_ID = %s
ORDER BY m.property_type, m.listing_ID
