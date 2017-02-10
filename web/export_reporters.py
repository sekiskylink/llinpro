import psycopg2
import psycopg2.extras
from settings import config
import getopt
import sys
from xlwt import Workbook

cmd = sys.argv[1:]
opts, args = getopt.getopt(
    cmd, 'd:',
    [])
districts = ''
for option, parameter in opts:
    if option == '-d':
        districts = parameter

conn = psycopg2.connect(
    "dbname=" + config["db_name"] + " host= " + config["db_host"] + " port=" + config["db_port"] +
    " user=" + config["db_user"] + " password=" + config["db_passwd"])
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

SQL = (
    "select initcap(a.firstname) || ' ' || initcap(a.lastname) as name, a.telephone, "
    "a.alternate_tel, a.role, a.email, district, loc_name as reporting_location, b.username "
    "created_by from reporters_view4 a, users b where a.created_by = b.id ")

if districts:
    SQL += " AND district IN (%s)" % ','.join(["'%s'" % i for i in districts.split(',')])
    fname = '_'.join(districts.split(','))
else:
    fname = 'reporters_all'

headings = ['Name', 'Telephone', 'Atl Telephone', 'Role', 'Email', 'District', 'Reporting Locatiom', 'Created By']
cur.execute(SQL)
data = cur.fetchall()[:65530]
row_len = len(data)

book = Workbook(encoding='utf-8')
sheet1 = book.add_sheet('Sheet 1')
for i, v in enumerate(headings):
    sheet1.write(0, i, v)
    sheet1.col(i).width = 4050
s = 0
for i in xrange(row_len):
    s += 1
    row = sheet1.row(s)
    for k in xrange(len(headings)):
        row.write(k, data[i][k])
sheet1.flush_row_data()
book.save("%s/downloads/%s.xls" % (
    config.get('static_directory', '/var/www/llinpro/web/static'), fname))

conn.close()
