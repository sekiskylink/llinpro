#!/usr/bin/env python
import psycopg2
import psycopg2.extras
import json
import requests
import logging
from settings import config

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(process)d] %(levelname)-4s:  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='/var/log/llin/llin_sched.log',
    filemode='a'
)

# To handle Json in DB well
psycopg2.extras.register_default_json(loads=lambda x: x)
psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)

conn = psycopg2.connect(
    "dbname=" + config["db_name"] + " host= " + config["db_host"] + " port=" + config["db_port"] +
    " user=" + config["db_user"] + " password=" + config["db_passwd"])
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)


def post_request(data, url=config['default_api_uri']):
    response = requests.post(url, data=data, headers={
        'Content-type': 'application/json',
        'Authorization': 'Token %s' % config['api_token']})
    return response


def sendsms(params):  # params has the sms params
    res = requests.get(config["smsurl"], params=params)
    return res.text

cur.execute(
    "SELECT id, params::text, type FROM schedules WHERE to_char(run_time, 'yyyy-mm-dd HH:MI')"
    " = to_char(now(), 'yyyy-mm-dd HH:MI') "
    " AND status = 'ready' FOR UPDATE NOWAIT")
res = cur.fetchall()
sched_len = len(res)
if sched_len:
    logging.info("Scheduler got %s SMS/URL/ContactPushes to send out" % sched_len)
for r in res:
    # cur.execute("SELECT id FROM schedules WHERE id = %s FOR UPDATE NOWAIT", [r["id"]])
    params = json.loads(r["params"])
    try:
        if r['type'] == 'sms':
            response = sendsms(params)
            status = 'completed' if 'Accepted' in response else 'failed'
            cur.execute("UPDATE schedules SET status = %s WHERE id = %s", [status, r["id"]])
            conn.commit()
            logging.info(
                "Scheduler run: [schedid:%s] [status:%s] [msg:%s]" % (r["id"], status, params["text"]))
        elif r['type'] == 'push_contact':  # push RapidPro contacts
            resp = post_request(json.dumps(params))
            if resp.status_code in (200, 201, 203, 204):
                status = 'completed'
            else:
                status = 'failed'
            cur.execute("UPDATE schedules SET status = %s WHERE id = %s", [status, r["id"]])
            conn.commit()
            logging.info(
                "Scheduler run: [schedid:%s] [status:%s] [push_contacts:%s]" % (r["id"], status, params["phone"]))
    except Exception as e:
        logging.error("Scheduler Failed on [schedid:%s], [reason:%s]" % (r["id"], str(e)))
conn.close()
