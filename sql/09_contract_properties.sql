SELECT m.*, d.project_name
FROM metrics m LEFT JOIN development_project d ON d.project_ID = m.project_ID
WHERE m.area_ID = %s AND m.property_type = %s AND m.contract_year = %s
ORDER BY m.listing_ID
