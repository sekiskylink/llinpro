# -*- coding: utf-8 -*-

"""Default options for the application.
"""

DEBUG = False

SESSION_TIMEOUT = 3600  # 1 Hour

HASH_KEY = ''
VALIDATE_KEY = ''
ENCRYPT_KEY = ''
SECRET_KEY = ''

PAGE_LIMIT = 25

QUANTITY_PER_BALE = 40
SMS_OFFSET_TIME = 5


def absolute(path):
    """Get the absolute path of the given file/folder.

    ``path``: File or folder.
    """
    import os
    PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(PROJECT_DIR, path))

config = {
    'db_name': 'llin',
    'db_host': 'localhost',
    'db_user': '',
    'db_passwd': '',
    'db_port': '',
    'logfile': '/tmp/llin-web.log',
    # Network RegEx for Kannel logs
    'network_regex': {
        'mtn': '256(3[19]|7[78])',
        'airtel': '2567[05]',
        'africel': '25679',
        'utl': '25671',
        'others': '256(3[19]|41|7[015789])'  # opssite of
    },
    'shortcode': '6400',
    # 'default_api_uri': 'http://hiwa.LLIN.co.ug/api/v1/contacts.json',
    'smsurl': 'http://localhost:13013/cgi-bin/sendsms?username=foo&password=bar',
    'default_api_uri': 'http://localhost:8000/api/v1/contacts.json',
    'api_token': 'c8cde9dbbdda6f544018e9321d017e909b28ec51',
    'api_url': 'http://localhost:8000/api/v1/',
    'national_reporters': ['HMU', 'District Supervisor', 'Subcounty Supervisor', 'Logistics Sub Committee'],
    'district_reporters': ['DSO', 'DHO', 'DHE', 'RDC'],
    'subcounty_reporters': ['Subcounty Chief', 'Subcounty Store Manager', 'LC3'],
    'village_reporters': ['VHT'],
    'national_sms_template': (
        "%(subcounty)s sub-county of %(district)s district is being sent %(quantity)s bales of nets. "
        " Delievery Note Number: %(waybill)s "),
    'driver_sms_template': (
        "You're delivering %(quantity)s bales of nets to %(subcounty)s sub-county of %(district)s district. "
        " Delivery Note Number: %(waybill)s. Once delivered/offloaded, please send "
        "\"DEL %(waybill)s %(quantity)s\" to %(shortcode)s."),
    'receive_subcounty_nets_sms_template': (
        "%(subcounty)s sub-county of %(district)s district has received %(quantity)s bales of nets. "
        " Delievery Note Number: %(waybill)s "),
    'receive_village_nets_sms_template': (
        "%(village)s village of %(subcounty)s subcounty has received %(quantity)s nets."
    ),
    'household_nets_sms_template': (
        "VHT (%(vht)s) has distributed %(quantity)s nets in %(village)s village of %(subcounty)s Sub-county"
    )

}

# the order of fields in the reporter upload excel file
EXCEL_UPLOAD_ORDER = {
    'name': 0,
    'telephone': 1,
    'alternate_tel': 2,
    'role': 3,
    'subcounty': 4,
    'parish': 5,
    'village': 6,
    'village_code': 7
}

try:
    from local_settings import *
except ImportError:
    pass
