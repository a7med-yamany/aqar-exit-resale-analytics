"""Narrow, user-approved developer identity migration; caller owns the transaction."""
import json
from pathlib import Path

MANIFEST = json.loads(Path(__file__).with_suffix('.json').read_text(encoding='utf-8'))


def merge_developers(conn, *, manifest=None):
    """Merge confirmed aliases into ID 38; never commit or disable FK checks."""
    if conn.get_autocommit():
        raise ValueError('Developer merge requires an explicit transaction.')
    manifest = MANIFEST if manifest is None else manifest
    target = manifest['canonical_id']
    aliases = {int(k): v for k, v in manifest['aliases'].items()}
    ids = [target, *aliases]
    slots = ','.join(['%s'] * len(ids))
    old_slots = ','.join(['%s'] * len(aliases))
    with conn.cursor() as cur:
        cur.execute('SAVEPOINT developer_identity_merge')
        try:
            cur.execute('''SELECT TABLE_NAME,COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA=DATABASE() AND REFERENCED_TABLE_NAME=%s''', ('developer',))
            refs = {(r['TABLE_NAME'], r['COLUMN_NAME']) for r in cur.fetchall()}
            if refs != {('develops', 'dev_ID'), ('property', 'direct_dev_ID')}:
                raise ValueError('Unexpected developer reference; migration requires review.')
            cur.execute(f'SELECT * FROM developer WHERE dev_ID IN ({slots}) ORDER BY dev_ID FOR UPDATE', ids)
            names = {r['dev_ID']: r['dev_name'] for r in cur.fetchall()}
            expected = {target: manifest['canonical_name'], **aliases}
            if names not in (expected, {target: manifest['canonical_name']}):
                raise ValueError('Developer identity names or IDs differ from the approved manifest.')
            cur.execute(f'SELECT project_ID,dev_ID FROM develops WHERE dev_ID IN ({slots}) FOR UPDATE', ids)
            links = list(cur.fetchall())
            projects = {r['project_ID'] for r in links}
            canonical_projects = {r['project_ID'] for r in links if r['dev_ID'] == target}
            cur.execute(f'SELECT property_ID FROM property WHERE direct_dev_ID IN ({slots}) FOR UPDATE', ids)
            cur.fetchall()
            cur.execute(f'''SELECT COUNT(*) AS n FROM listing l JOIN property p ON p.property_ID=l.property_ID
                WHERE EXISTS (SELECT 1 FROM develops d WHERE d.project_ID=p.project_ID AND d.dev_ID IN ({slots}))
                OR (p.project_ID IS NULL AND p.direct_dev_ID IN ({slots}))''', ids + ids)
            distinct_listings = cur.fetchone()['n']
            if len(names) == 1:
                # FK checks ensure removed aliases cannot still have incoming references.
                result = {'status': 'already_merged', 'canonical_id': target,
                          'projects': len(projects), 'distinct_listings': distinct_listings}
            else:
                new_links = [(p, target) for p in sorted(projects - canonical_projects)]
                if new_links:
                    cur.executemany('INSERT INTO develops(project_ID,dev_ID) VALUES (%s,%s)', new_links)
                cur.execute(f'UPDATE property SET direct_dev_ID=%s WHERE direct_dev_ID IN ({old_slots})',
                            [target, *aliases])
                direct_updated = cur.rowcount
                cur.execute(f'DELETE FROM develops WHERE dev_ID IN ({old_slots})', list(aliases))
                old_links = cur.rowcount
                cur.execute(f'DELETE FROM developer WHERE dev_ID IN ({old_slots})', list(aliases))
                if cur.rowcount != len(aliases):
                    raise AssertionError('Unexpected number of removed developer aliases.')
                cur.execute('SELECT COUNT(*) AS n FROM develops WHERE dev_ID=%s', (target,))
                if cur.fetchone()['n'] != len(projects):
                    raise AssertionError('Merged developer lost a project association.')
                cur.execute('''SELECT COUNT(*) AS n FROM listing l JOIN property p ON p.property_ID=l.property_ID
                    WHERE EXISTS (SELECT 1 FROM develops d WHERE d.project_ID=p.project_ID AND d.dev_ID=%s)
                    OR (p.project_ID IS NULL AND p.direct_dev_ID=%s)''', (target, target))
                if cur.fetchone()['n'] != distinct_listings:
                    raise AssertionError('Merged developer listing union changed.')
                result = {'status': 'merged', 'canonical_id': target, 'removed_aliases': sorted(aliases),
                          'projects': len(projects), 'distinct_listings': distinct_listings,
                          'old_links_removed': old_links, 'new_links_added': len(new_links),
                          'duplicate_links_collapsed': old_links - len(new_links),
                          'direct_references_updated': direct_updated}
            cur.execute('RELEASE SAVEPOINT developer_identity_merge')
            return result
        except BaseException:
            cur.execute('ROLLBACK TO SAVEPOINT developer_identity_merge')
            cur.execute('RELEASE SAVEPOINT developer_identity_merge')
            raise
