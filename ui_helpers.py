"""Presentation helpers; keep monetary arithmetic in Decimal until display."""
import csv
from decimal import Decimal
import io


def amount(value, places=0):
    return 'Not available' if value is None else f'{Decimal(str(value)):,.{places}f}'


def csv_download(rows):
    stream = io.StringIO(newline='')
    if rows:
        writer = csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: "'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@','\t','\r')) else v
                             for k,v in row.items()})
    return stream.getvalue().encode('utf-8-sig')


def filter_properties(rows, property_type=None, year=None, minimum=None, maximum=None,amenities=()):
    return [r for r in rows
            if (property_type is None or r['property_type'] == property_type)
            and (year is None or r['contract_year'] == year)
            and all(a in r.get('amenities',()) for a in amenities)
            and (minimum is None or r['resale_price'] is not None and r['resale_price'] >= Decimal(str(minimum)))
            and (maximum is None or r['resale_price'] is not None and r['resale_price'] <= Decimal(str(maximum)))]


LABELS = {
    'property_ID':'Property reference','listing_ID':'Listing reference',
    'project_name':'Development','area_name':'Area','property_type':'Property type',
    'resale_price':'Resale price (EGP)','resale_price_per_sqm':'Price / m² (EGP)',
    'area_sqm':'Area (m²)','No_bedrooms':'Bedrooms','No_bathrooms':'Bathrooms',
    'down_payment':'Required down payment (EGP)','cash_required_now':'Cash now incl. fees (EGP)',
    'remaining_balance':'Remaining balance (EGP)','market_price':'Market price (EGP)',
    'gain_over_current_value':'Gain over market (EGP)','contract_year':'Contract year',
    'area_type_avg_price_per_sqm':'Area/type avg. price / m² (EGP)',
    'area_type_priced_listings':'Area/type priced listings',
    'listing_count':'Listings','property_count':'Properties','priced_listings':'Priced listings',
    'avg_price_per_sqm':'Avg. price / m² (EGP)','resale_inventory':'Listings',
    'resale_amount':'Resale amount (EGP)','avg_gain_over_market':'Avg. gain (EGP)',
    'total_gain_over_market':'Total known gain (EGP)','gain_known_listings':'Listings with gain',
    'rank_in_type':'Rank','dev_name':'Developer',
    'avg_required_down_payment':'Avg. required down payment (EGP)',
    'avg_cash_required_now':'Avg. cash now incl. fees (EGP)',
    'avg_resale_price':'Avg. resale price (EGP)',
    'avg_monthly_installment':'Avg. monthly installment (EGP)',
    'avg_annual_installment':'Avg. annual installment (EGP)',
    'avg_down_payment':'Avg. required down payment (EGP)',
    'avg_discount_amount':'Avg. discount (EGP)','avg_discount_pct':'Avg. discount (%)',
    'avg_contract_age_years':'Avg. contract age (years)','avg_market_price':'Avg. market price (EGP)',
    'installment_known_listings':'Listings with installments',
    'down_payment_known_listings':'Listings with down payment',
    'discount_known_listings':'Listings with discount',
    'discount_pct_known_listings':'Listings with discount %',
    'contract_age_known_listings':'Listings with contract age',
    'market_price_known_listings':'Listings with market price',
}


def labeled_rows(rows, columns):
    return [{LABELS.get(k,k): row.get(k) for k in columns} for row in rows]
