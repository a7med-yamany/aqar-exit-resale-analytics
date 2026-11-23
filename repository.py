"""Application-facing SQL operations; caller owns commit/rollback.

Use db.transaction() for writes. No function interpolates user input into SQL.
"""
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
import json
import re

SQL_DIR = Path(__file__).resolve().parent / 'sql'


def positive_id(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f'{name} must be a positive integer.')
    return value


def email(value):
    value = str(value).strip()
    if len(value) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
        raise ValueError('Enter a valid email address (maximum 254 characters).')
    return value


def money(value):
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('Prices must be finite nonnegative numbers.') from exc
    if not result.is_finite() or result < 0:
        raise ValueError('Prices must be finite nonnegative numbers.')
    return result


class Repository:
    def __init__(self, connection):
        self.connection = connection

    def _sql(self, name, analytics=False):
        text = (SQL_DIR / (name + '.sql')).read_text(encoding='utf-8')
        if analytics:
            text = (SQL_DIR / '00_metrics.sql').read_text(encoding='utf-8') + '\n' + text
        return text

    def _read(self, sql, params=()):
        with self.connection.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def register_user(self, user_email, username, gender, birthdate, area_ids):
        user_email = email(user_email)
        username = str(username).strip()
        if not username or len(username) > 100:
            raise ValueError('Username must contain 1 to 100 characters.')
        if gender is not None and (not isinstance(gender, str) or len(gender) > 30):
            raise ValueError('Gender must be at most 30 characters or None.')
        if type(birthdate) is not date or not date(1900, 1, 1) <= birthdate <= date.today():
            raise ValueError('Birthdate must be a real date between 1900 and today.')
        areas = sorted({positive_id(a, 'area_ID') for a in area_ids})
        if not areas:
            raise ValueError('Select at least one focus area.')
        with self.connection.cursor() as cur:
            # Savepoint makes registration atomic even if a caller catches the error.
            cur.execute('SAVEPOINT registration')
            try:
                cur.execute(self._sql('01_register_user'),
                            (user_email, username, gender, birthdate))
                cur.executemany(self._sql('01_register_focus'),
                                [(a, user_email) for a in areas])
            except BaseException:
                cur.execute('ROLLBACK TO SAVEPOINT registration')
                raise
            finally:
                cur.execute('RELEASE SAVEPOINT registration')
        return user_email

    def add_review(self, project_id, user_email, rating, text):
        positive_id(project_id, 'project_ID')
        user_email = email(user_email)
        if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 10:
            raise ValueError('Rating must be an integer from 1 to 10.')
        if not isinstance(text, str) or not text.strip() or len(text.encode('utf-8')) > 65535:
            raise ValueError('Review text is required and must fit a MySQL TEXT field.')
        with self.connection.cursor() as cur:
            cur.execute('''SELECT EXISTS(SELECT 1 FROM `user` WHERE user_email=%s) AS profile_exists,
                EXISTS(SELECT 1 FROM development_project WHERE project_ID=%s) AS project_exists''',
                (user_email,project_id))
            parents=cur.fetchone()
            if not parents['profile_exists']:
                raise ValueError('No registered profile matches this email. Create a profile in Register profile first, or use your registered email.')
            if not parents['project_exists']:
                raise ValueError('This project is no longer available. Refresh the data and choose another development.')
            cur.execute(self._sql('02_add_review'), (project_id, user_email, rating, text.strip()))

    def project_reviews(self, project_id):
        return self._read(self._sql('03_project_reviews'),
                          (positive_id(project_id, 'project_ID'),))

    def top_projects(self, metric='inventory', property_type=None):
        metrics = {'inventory': 'resale_inventory', 'resale_amount': 'resale_amount',
                   'gain': 'avg_gain_over_market'}
        if metric not in metrics:
            raise ValueError('Metric must be inventory, resale_amount or gain.')
        # Only the fixed allowlist above supplies an SQL identifier.
        sql = self._sql('04_top_projects', True).format(metric=metrics[metric])
        rows = self._read(sql)
        return rows if property_type is None else [r for r in rows if r['property_type'] == property_type]

    def project_statistics(self, project_id):
        return self._read(self._sql('05_project_statistics', True),
                          (positive_id(project_id, 'project_ID'),))

    def area_properties(self, area_id):
        rows=self._read(self._sql('06_area_properties', True),
                        (positive_id(area_id, 'area_ID'),))
        for row in rows:
            row['amenities']=json.loads(row.pop('amenities_json') or '[]')
        return rows

    def search_properties(self, area_id, min_price, max_price, amenities=()):
        positive_id(area_id, 'area_ID')
        low = money(min_price) if min_price is not None else None
        high = money(max_price) if max_price is not None else None
        if low is not None and high is not None and low > high:
            raise ValueError('Minimum price must not exceed maximum price.')
        if isinstance(amenities, str):
            raise ValueError('Amenities must be a list, not a single string.')
        amenities = list(dict.fromkeys(amenities))
        if any(not isinstance(a, str) or not a.strip() or len(a) > 200 for a in amenities):
            raise ValueError('Each amenity must be a nonblank string of at most 200 characters.')
        clauses = []
        for _ in amenities:
            clauses.append('AND EXISTS (SELECT 1 FROM propertyamenity pa '
                           'WHERE pa.property_ID = m.property_ID AND pa.amenities = %s)')
        sql = self._sql('07_search_properties', True).format(amenity_filter='\n'.join(clauses))
        return self._read(sql, (area_id, low, low, high, high, *amenities))

    def top_developers(self):
        return self._read(self._sql('08_top_developers', True))

    def contract_properties(self, area_id, property_type, contract_year):
        positive_id(area_id, 'area_ID')
        if not isinstance(property_type, str) or not property_type.strip() or len(property_type) > 80:
            raise ValueError('Select a valid property type.')
        if isinstance(contract_year, bool) or not isinstance(contract_year, int) or not 1901 <= contract_year <= 2155:
            raise ValueError('Contract year must be between 1901 and 2155.')
        return self._read(self._sql('09_contract_properties', True),
                          (area_id, property_type, contract_year))

    def market_summary(self):
        return self._read(self._sql('10_market_summary', True))

    def lookup_options(self):
        return {
            'areas': self._read('SELECT area_ID, area_name FROM area ORDER BY area_name, area_ID'),
            'projects': self._read('SELECT project_ID, project_name, area_ID FROM development_project ORDER BY project_name, project_ID'),
            'property_types': self._read('SELECT DISTINCT type FROM property ORDER BY type'),
            'amenities': self._read('SELECT DISTINCT amenities FROM propertyamenity ORDER BY amenities'),
            'contract_years': self._read('SELECT DISTINCT contract_year FROM listing WHERE contract_year IS NOT NULL ORDER BY contract_year DESC'),
        }

    def overview_counts(self):
        return self._read('''SELECT (SELECT COUNT(*) FROM listing) AS listings,
            (SELECT COUNT(*) FROM development_project) AS projects,
            (SELECT COUNT(*) FROM developer) AS developers,
            (SELECT COUNT(*) FROM area) AS areas''')[0]

    def listing_details(self, listing_id):
        if not isinstance(listing_id,str) or not listing_id or len(listing_id)>36:
            raise ValueError('Invalid listing reference.')
        rows = self._read(self._sql('00_metrics')+'''
            SELECT m.*, a.area_name, d.project_name FROM metrics m
            JOIN area a ON a.area_ID=m.area_ID
            LEFT JOIN development_project d ON d.project_ID=m.project_ID
            WHERE m.listing_ID=%s''',(listing_id,))
        if not rows:
            return None
        row = rows[0]
        row['amenities'] = [r['amenities'] for r in self._read(
            'SELECT amenities FROM propertyamenity WHERE property_ID=%s ORDER BY amenities',
            (row['property_ID'],))]
        return row
