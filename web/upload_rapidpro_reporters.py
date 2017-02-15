#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = "Sekiwere Samuel"

import requests
import json
import psycopg2
import psycopg2.extras
from settings import config
import phonenumbers
import getopt
import sys
import datetime

cmd = sys.argv[1:]
opts, args = getopt.getopt(
    cmd, 'd:',
    [])

now = datetime.datetime.now()
sdate = now - datetime.timedelta(days=1, minutes=5)
from_date = sdate.strftime('%Y-%m-%d %H:%M')

for option, parameter in opts:
    if option == '-d':
        from_date = parameter


def post_request(data, url=config['default_api_uri']):
    response = requests.post(url, data=data, headers={
        'Content-type': 'application/json',
        'Authorization': 'Token %s' % config['api_token']})
    return response


def get_request(url):
    response = requests.get(url, headers={
        'Content-type': 'application/json',
        'Authorization': 'Token %s' % config['api_token']})
    return response


def get_available_fields():
    response = requests.get(
        '%sfields.json' % config['api_url'], headers={
            'Content-type': 'application/json',
            'Authorization': 'Token %s' % config['api_token']})
    results = [k['key'] for k in json.loads(response.text)['results']]
    return results


def format_msisdn(msisdn=None):
    """ given a msisdn, return in E164 format """
    assert msisdn is not None
    num = phonenumbers.parse(msisdn, getattr(config, 'country', 'UG'))
    is_valid = phonenumbers.is_valid_number(num)
    if not is_valid:
        return None
    return phonenumbers.format_number(
        num, phonenumbers.PhoneNumberFormat.E164)  # .replace('+', '')


def add_reporter_fields():
    our_fields = [
        {'label': 'facility', 'value_type': 'T'},
        {'label': 'facilityuuid', 'value_type': 'T'},
        {'label': 'district', 'value_type': 'I'},
        {'label': 'Subcounty', 'value_type': 'I'},
        {'label': 'village', 'value_type': 'T'},
        {'label': 'reporting location', 'value_type': 'T'},
    ]
    fields = get_available_fields()
    for f in our_fields:
        if f['label'] not in fields:
            res = post_request(
                json.dumps(f), '%sfields.json' % config['api_url'])
            print res.text


add_reporter_fields()
conn = psycopg2.connect(
    "dbname=" + config["db_name"] + " host= " + config["db_host"] + " port=" + config["db_port"] +
    " user=" + config["db_user"] + " password=" + config["db_passwd"])
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

cur.execute(
    "UPDATE reporters set reporting_location = get_subcounty_id(reporting_location) "
    "WHERE id in (SELECT reporter_id FROM reporter_groups_reporters WHERE group_id IN "
    "(SELECT id FROM reporter_groups WHERE name IN ('Subcounty Store Manager', 'Subcounty Chief')))")
conn.commit()

cur.execute(
    "SELECT a.id, a.firstname || ' ' || a.lastname as name, a.telephone, a.alternate_tel, "
    "a.email, get_location_name(a.district_id) AS district, get_reporter_groups(a.id) AS role, "
    "b.code as reporting_location FROM reporters a, locations b WHERE a.reporting_location = b.id "
    "AND a.created >= %s", [from_date]
)

res = cur.fetchall()
print "==>", res
if res:
    for r in res:
        print r
        district = r["district"]
        fields = {
            "reporting location": r['reporting_location']
        }
        if district:
            fields["district"] = district
        phone = format_msisdn(r['telephone'])
        alt_phone = r['alternate_tel']
        if phone:
            data = {
                "name": r['name'],
                "phone": phone,
                "email": r['email'],
                "groups": [r['role']],
                "fields": fields
            }
            post_data = json.dumps(data)
            resp = post_request(post_data)
            # print post_data
            print resp.text
        if alt_phone:
            alt_phone = format_msisdn(alt_phone)
            data["phone"] = alt_phone
            post_data = json.dumps(data)
            resp = post_request(post_data)
            print resp.text
