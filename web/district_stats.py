#!/usr/bin/env python
import psycopg2
import psycopg2.extras
import simplejson
import pprint
from settings import config


conn = psycopg2.connect(
    "dbname=" + config['db_name'] + " host= " + config['db_host'] + " port=" +
    config['db_port'] + " user=" + config['db_user'] + " password=" + config['db_passwd'])
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

district_stats = {}
cur.execute("SELECT id, name, child_count(id) children FROM locations WHERE type_id = 3")
res = cur.fetchall()
for r in res:
    district_stats['%s' % r['id']] = {'name': r['name'], 'total_subcounties': r['children']}
# pprint.pprint(district_stats)

for k in district_stats.keys():
    cur.execute(
        "SELECT district_id, district, destination subcounty, sum(quantity_bales) total_bales "
        "FROM distribution_log_w2sc_view "
        "WHERE district_id = %s "
        "GROUP by district_id, district, subcounty "
        "ORDER by district, subcounty", [k])
    res = cur.fetchall()
    subcounties_served = len(res)
    district_stats[k]['subcounties_served'] = subcounties_served
    total_bales = 0
    for r in res:
        total_bales += r['total_bales']
    district_stats[k]['total_bales'] = total_bales
    try:
        coverage = (float(subcounties_served) / district_stats[k]['total_subcounties']) * 100
    except:
        coverage = 0
    district_stats[k]['coverage'] = float('%.2f' % coverage)
    if coverage == 100:
        # color = 'rgba(50, 205, 50, 0.7)'
        color = 'rgba(0, 128, 0, 0.7)'
    elif coverage >= 75 and coverage < 100:
        color = 'rgba(0, 255, 0, 0.8)'
        # color = 'rgba(255, 215, 0, 0.8)'
    elif coverage >= 50 and coverage < 75:
        color = 'rgba(255, 215, 0, 0.8)'
    elif coverage > 0 and coverage < 50:
        color = 'rgba(220, 20, 60, 0.7)'
    else:
        color = 'rgba(255, 100, 50, 0.1)'
    district_stats[k]['color'] = color

    # now save stats if not already in DB
    cur.execute("SELECT id FROM district_stats WHERE district_id = %s", [k])
    res = cur.fetchone()
    if res:
        cur.execute(
            "UPDATE district_stats SET stats = %s, updated = NOW() WHERE id = %s ",
            [psycopg2.extras.Json(district_stats[k], dumps=simplejson.dumps), res['id']])
    else:
        cur.execute(
            "INSERT INTO district_stats (district_id, stats, updated) "
            "VALUES (%s, %s, NOW())",
            [k, psycopg2.extras.Json(district_stats[k], dumps=simplejson.dumps)])
    conn.commit()
pprint.pprint(district_stats)
conn.close()
