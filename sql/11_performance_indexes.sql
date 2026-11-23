-- Additive performance migration, applied idempotently by optimize_database.py.
-- No source-data, column, primary-key or foreign-key changes.
CREATE INDEX idx_property_area_type ON property (area_ID,type);
CREATE INDEX idx_listing_year_property ON listing (contract_year,property_ID);
