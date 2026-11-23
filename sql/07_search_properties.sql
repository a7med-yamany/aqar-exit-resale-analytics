SELECT m.*, d.project_name
FROM metrics m LEFT JOIN development_project d ON d.project_ID = m.project_ID
WHERE m.area_ID = %s
AND (%s IS NULL OR m.resale_price >= %s)
AND (%s IS NULL OR m.resale_price <= %s)
{amenity_filter}
ORDER BY m.resale_price, m.listing_ID
