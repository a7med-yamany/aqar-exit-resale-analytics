SELECT d.project_ID, d.project_name, d.location_detail, a.area_name,
       m.property_type, COUNT(m.listing_ID) AS listing_count,
       COUNT(m.resale_price_per_sqm) AS priced_listings,
       AVG(m.resale_price_per_sqm) AS avg_price_per_sqm
FROM development_project d JOIN area a ON a.area_ID = d.area_ID
LEFT JOIN metrics m ON m.project_ID = d.project_ID
WHERE d.project_ID = %s
GROUP BY d.project_ID, d.project_name, d.location_detail, a.area_name, m.property_type
ORDER BY m.property_type
