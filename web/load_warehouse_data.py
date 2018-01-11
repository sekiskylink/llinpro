#!/usr/bin/env python
import psycopg2
import psycopg2.extras
import getopt
import sys
import requests
# import pprint
from datetime import datetime
from openpyxl import load_workbook
from settings import config
from settings import BASE_DIR
from settings import DOMAIN

TEMPLATES_DIR = BASE_DIR + "/static/downloads/"

cmd = sys.argv[1:]
opts, args = getopt.getopt(
    cmd, 'f:d:u:h',
    ['upload-file', 'district', 'user'])


def usage():
    return """usage: python load_warehouse_data.py [-f <excel-file>]  [-u <username>] [-h]
    -f path to input excel file to be imported
    -u user account importing excel file
    -h Show this message
    """

user = "api_user"
upload_file = ""
district = ""
for option, parameter in opts:
    if option == '-f':
        upload_file = parameter
    if option == '-u':
        user = parameter.strip()
    if option == '-h':
        print usage()
        sys.exit(1)

if not upload_file:
    print "An excel file is expected!"
    sys.exit(1)

order = {
    'po_number': 0, 'waybill': 1, 'goods_received_note': 2, 'manufacturer': 3, 'entry_date': 4,
    'quantity_bales': 5, 'remarks': 6, 'warehouse': 7, 'warehouse_branch': 8, 'funding_source': 9, 'nets_type': 10,
    'nets_color': 11, 'nets_size': 12, 'unbs_samples': 13, 'country': 14
}

print upload_file

conn = psycopg2.connect(
    "dbname=" + config["db_name"] + " host= " + config["db_host"] + " port=" + config["db_port"] +
    " user=" + config["db_user"] + " password=" + config["db_passwd"])
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

manufacturers = {}
cur.execute("SELECT id, name FROM manufacturers")
rs = cur.fetchall()
for r in rs:
    manufacturers[r['name']] = r['id']

fundingSources = {}
cur.execute("SELECT id, name FROM funding_sources")
rs = cur.fetchall()
for r in rs:
    fundingSources[r['name']] = r['id']

warehouses = {}
cur.execute("SELECT id, name FROM warehouses")
rs = cur.fetchall()
for r in rs:
    warehouses[r['name']] = r['id']

warehouseBranches = {}
cur.execute("SELECT id, name FROM warehouse_branches")
rs = cur.fetchall()
for r in rs:
    warehouseBranches[r['name']] = r['id']

countries = {}
cur.execute("SELECT id, name FROM countries")
rs = cur.fetchall()
for r in rs:
    countries[r['name']] = r['id']


wb = load_workbook(upload_file, read_only=True)
print wb.get_sheet_names()
# get all the data in the different sheets
data = []
for sheet in wb:
    # print sheet.title
    j = 0
    for row in sheet.rows:
        if j > 0:
            # val = ['%s' % i.value for i in row]
            val = [u'' if i.value is None else unicode(i.value) for i in row]
            # print val
            data.append(val)
        j += 1
# print data
# start processing data in the sheets
ignored = []

for d in data:
    if not (d[order['waybill']] and d[order['goods_received_note']]):
        print "One of the mandatory fields (waybill or goods_received_note) missing"
        ignored.append(d)
        print "================================================================="
        print "=", d[5]
        print "================================================================="
        continue
    # print "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
    # print "#", d[5]
    # print "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"

    po_number = d[order['po_number']].strip()
    waybill = d[order['waybill']].strip()
    goods_received_note = d[order['goods_received_note']].strip()
    manufacturer = d[order['manufacturer']].strip()
    entry_date = d[order['entry_date']].strip()
    quantity_bales = d[order['quantity_bales']].strip()
    remarks = d[order['remarks']].strip()
    warehouse = d[order['warehouse']].strip()
    warehouse_branch = d[order['warehouse_branch']].strip().capitalize()
    funding_source = d[order['funding_source']].strip()
    nets_type = d[order['nets_type']].strip().strip('.')
    nets_size = d[order['nets_size']].strip().strip('.')
    nets_color = d[order['nets_color']].strip()
    unbs_samples = d[order['unbs_samples']].strip()
    country = d[order['country']].strip()
    unbs_samples = unbs_samples if unbs_samples else 0
    if entry_date:
        try:
            entry_date = datetime.strptime(entry_date, "%Y-%m-%d %H:%M:%S").strftime('%Y-%m-%d')
        except:
            entry_date = ''
    # print "=====================>", _phone
    if waybill and quantity_bales and goods_received_note:
        try:
            params = {
                'po_number': po_number, 'waybill': waybill, 'goods_received_note': goods_received_note,
                'manufacturer': manufacturers[manufacturer], 'funding_source': fundingSources[funding_source],
                'quantity': quantity_bales, 'made_in': countries[country], 'nets_color': nets_color,
                'nets_size': nets_size, 'entry_date': entry_date, 'remarks': remarks, 'nets_type': nets_type,
                'warehouse': warehouses[warehouse], 'warehouse_branch': warehouseBranches[warehouse_branch],
                'country': countries[country], 'unbs_sample': unbs_samples,
                'caller': 'api', 'user': user}
            # pprint.pprint(params)
            resp = requests.post('%s/api/v1/warehousedataapi' % DOMAIN, data=params)
            print resp.text
        except Exception, e:
            pass
        # pprint.pprint(params)
    else:
        print "ZZZZZZZZZZ", d

# val = 0
# if ignored:
#     print ignored
#     for l in ignored:
#         quantity_bales = l[order['quantity_bales']].strip()
#         if quantity_bales:
#             qty = int(quantity_bales)
#             val += qty
# print "TOTAL IGNORED:", val

conn.close()
