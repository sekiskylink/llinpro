#!/usr/bin/env python
import os
import datetime
import argparse
import psycopg2
import psycopg2.extras
import simplejson
import pprint
from settings import config

parser = argparse.ArgumentParser()
parser.add_argument('-m', '--month', help='month to generate stats for')
parser.add_argument('-v', '--verbose', help='Turn on verbose output', action='store_true')
args = parser.parse_args()

# connection to temba DB
conn = psycopg2.connect(
    "dbname=" + config['db_name'] + " host= " + config['db_host'] + " port=" +
    config['db_port'] + " user=" + config['db_user'] + " password=" + config['db_passwd'])
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

NETWORK_REGEX = config.get('network_regex', {
    'mtn': '256(3[19]|7[78])',
    'airtel': '2567[05]',
    'africel': '25679',
    'utl': '25671',
    'others': '256(3[19]|41|7[015789])'  # opssite of
})

LOGS_DIR = config.get("kannel_log_dir", "/var/log/kannel")
SEARCH_FILES = "%s/kannel.access*" % LOGS_DIR

if args.month:
    MONTH = args.month
else:
    MONTH = datetime.datetime.now().strftime('%Y-%m')

# print "generating for =>", MONTH
stats = {MONTH: {}}
total_in = 0
total_out = 0

for k, v in NETWORK_REGEX.iteritems():
    if k != 'others':
        in_cmd = """zgrep "^%s" %s | grep "Receive SMS" | egrep -c "from:%s" """ % (MONTH, SEARCH_FILES, v)
        out_cmd = """zgrep "^%s" %s | grep "Sent SMS" | egrep -c "to:%s" """ % (MONTH, SEARCH_FILES, v)
    else:
        in_cmd = """zgrep "^%s" %s | grep "Receive SMS" | egrep -v -c "from:%s" """ % (MONTH, SEARCH_FILES, v)
        out_cmd = """zgrep "^%s" %s | grep "Sent SMS" | egrep -v -c "to:%s" """ % (MONTH, SEARCH_FILES, v)

    # print in_cmd
    # print out_cmd
    incomming = os.popen(in_cmd)
    outgoing = os.popen(out_cmd)
    in_count = incomming.read().strip()
    out_count = outgoing.read().strip()
    stats[MONTH]["%s_in" % k] = in_count
    stats[MONTH]["%s_out" % k] = out_count
    total_in += int(in_count)
    total_out += int(out_count)

stats[MONTH]["total_in"] = total_in
stats[MONTH]["total_out"] = total_out

for k, v in stats.iteritems():
    cur.execute("SELECT id FROM kannel_stats WHERE month = %s", [k])
    res = cur.fetchone()
    if res:
        # print "res=>", res
        cur.execute(
            "UPDATE kannel_stats SET stats = %s, updated = NOW() WHERE id = %s ",
            [psycopg2.extras.Json(v, dumps=simplejson.dumps), res['id']])
    else:
        cur.execute(
            "INSERT INTO kannel_stats (month, stats, updated) "
            "VALUES (%s, %s, NOW())", [k, psycopg2.extras.Json(v, dumps=simplejson.dumps)])
    conn.commit()

if args.verbose:
    pprint.pprint(stats)
conn.close()
