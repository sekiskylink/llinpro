#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = "Sekiwere Samuel"

import requests
import json
import psycopg2
import psycopg2.extras
from settings import config
import phonenumbers


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
    "SELECT a.id, a.firstname || ' ' || a.lastname as name, a.telephone, a.alternate_tel, "
    "a.email, get_district(a.reporting_location) AS district, get_reporter_groups(a.id) AS role, "
    "b.code as reporting_location FROM reporters a, locations b WHERE a.reporting_location = b.id"
)

print format_msisdn('0782820208')
res = cur.fetchall()
if res:
    for r in res:
        print r
        fields = {
            "district": r['district'],
            "reporting location": r['reporting_location']

        }
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