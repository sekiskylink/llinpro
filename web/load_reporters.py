import xlrd
import phonenumbers
import getopt
import sys
import psycopg2
import psycopg2.extras
from settings import config
import settings

cmd = sys.argv[1:]
opts, args = getopt.getopt(cmd, 'f:', [])
filename = ''
for option, parameter in opts:
        if option == '-f':
            filename = parameter

print filename

order = getattr(settings, 'EXCEL_UPLOAD_ORDER', {
    'name': 0,
    'telephone': 1,
    'alternate_tel': 2,
    'role': 3,
    'subcounty': 4,
    'parish': 5,
    'village': 6,
    'village_code': 7
})

conn = psycopg2.connect(
    "dbname=" + config["db_name"] + " host= " + config["db_host"] + " port=" + config["db_port"] +
    " user=" + config["db_user"] + " password=" + config["db_passwd"])
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)


def format_msisdn(msisdn=""):
    """ given a msisdn, return in E164 format """
    if not msisdn:
        return ""
    msisdn = msisdn.replace(' ', '')
    num = phonenumbers.parse(msisdn, getattr(config, 'country', 'UG'))
    is_valid = phonenumbers.is_valid_number(num)
    if not is_valid:
        return ""
    return phonenumbers.format_number(
        num, phonenumbers.PhoneNumberFormat.E164)


def read_all_reporters(filename):
    wb = xlrd.open_workbook(filename)
    l = []
    # lets stick to sheet one only
    # num_of_sheets = wb.nsheets
    num_of_sheets = 1
    for i in xrange(num_of_sheets):
        sh = wb.sheet_by_index(i)
        for rownum in range(sh.nrows):
            vals = sh.row_values(rownum)
            l.append(vals)
    # print l
    return l


def load_reporters(data):
    IGNORED_ENTRIES = []
    for d in data:
        if not d[order['name']] or not d[order['telephone']]:
            print "No name or missing telephone"
            IGNORED_ENTRIES.append(d)
            continue
        _name = d[order['name']].strip()
        _name = ' '.join([pname.capitalize() for pname in _name.split(' ')])

        try:
            _phone = '%s' % (str(int(float(d[order['telephone']]))))
        except:
            _phone = ""
        try:
            _phone2 = '%s' % str(int(float(d[order['alternate_tel']]))) if d[order['alternate_tel']] else ''
        except:
            _phone2 = ""
        _role = d[order['role']].strip()
        _village_code = d[order['village_code']].strip()

        fphone = format_msisdn(_phone)
        fphone2 = format_msisdn(_phone2)
        if not (fphone and _village_code and _role):
            print "++++++++++++++++++++++=>", _phone
            continue
        names = _name.split(' ')
        if len(names) > 1:
            fname = names[0]
            lname = ' '.join(names[1:])
        else:
            fname = names[0]
            lname = ''
        print "=============>", format_msisdn(_phone), "=>", fname, "=>", lname, "=>", _role, "=>", _village_code
        reporter_id = 0
        cur.execute(
            "SELECT id FROM reporters WHERE replace(telephone, '+', '') = %s OR "
            "replace(alternate_tel, '+', '') = %s LIMIT 1",
            [fphone.replace('+', ''), fphone.replace('+', '')])
        res = cur.fetchone()
        if not res:
            res2 = None
            if fphone2:
                cur.execute(
                    "SELECT id FROM reporters WHERE replace(telephone, '+', '') = %s OR "
                    "replace(alternate_tel, '+', '') = %s LIMIT 1",
                    [fphone2.replace('+', ''), fphone2.replace('+', '')])
                res2 = cur.fetchone()
            if not res2:
                # we're confident reporter numbers are not in yet
                cur.execute(
                    "INSERT INTO reporters(firstname, lastname, telephone, alternate_tel, "
                    "reporting_location, district_id) VALUES(%s, %s, %s, %s, "
                    "(SELECT id FROM locations WHERE code = %s), get_district_id("
                    "(SELECT id FROM locations WHERE code = %s))) RETURNING id",
                    [fname, lname, fphone, fphone2, _village_code, _village_code])
                res3 = cur.fetchone()
                conn.commit()
                reporter_id = res3["id"]
                cur.execute(
                    "INSERT INTO reporter_groups_reporters(group_id, reporter_id) "
                    "VALUES((SELECT id FROM reporter_groups WHERE lower(name) = %s), %s)",
                    [_role.lower(), reporter_id])
                conn.commit()
        else:
            reporter_id = res["id"]
            print "Reporter %s: %s/%s already in system" % (_name, fphone, fphone2)
            cur.execute(
                "UPDATE reporters SET firstname = %s, lastname = %s, telephone = %s, "
                "alternate_tel = %s, reporting_location = (SELECT id FROM locations WHERE code = %s) "
                "WHERE id = %s",
                [fname, lname, fphone, fphone2, _village_code, reporter_id])
            cur.execute(
                "UPDATE reporter_groups_reporters SET group_id = "
                "(SELECT id FROM reporter_groups WHERE lower(name) = %s) WHERE reporter_id = %s ",
                [_role.lower(), reporter_id])
            conn.commit()

l = read_all_reporters(filename)
load_reporters(l[1:])
conn.close()
