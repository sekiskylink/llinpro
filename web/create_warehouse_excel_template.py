import xlsxwriter
import psycopg2
import psycopg2.extras
from datetime import date
from settings import config
from settings import BASE_DIR

TEMPLATES_DIR = BASE_DIR + "/static/downloads/"

conn = psycopg2.connect(
    "dbname=" + config["db_name"] + " host= " + config["db_host"] + " port=" + config["db_port"] +
    " user=" + config["db_user"] + " password=" + config["db_passwd"])
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

template_name = 'Warehouse_Log'
workbook = xlsxwriter.Workbook(
    TEMPLATES_DIR + "%s_Template.xlsx" % template_name, {'default_date_format': 'dd/mm/yyyy'})
# set some formats
text_format = workbook.add_format()
text_format.set_num_format('@')
text_format.set_font_size(14)
date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
date_format.set_font_size(14)
bold = workbook.add_format({'bold': True})
bold.set_font_size(14)

warehouse_list = []
cur.execute("SELECT id, name FROM warehouses ORDER BY name")
res = cur.fetchall()
for r in res:
    warehouse_list.append(r['name'])

warehouse_branches = []
cur.execute("SELECT id, name FROM warehouse_branches ORDER BY name")
res = cur.fetchall()
for r in res:
    warehouse_branches.append(r['name'])

net_types = [
    'Olyset', 'Olyset Plus', 'PermaNet 2.0.', 'PermaNet 3.0.',
    'Magnet', 'Duranet', 'Dawa Plus', 'Dava Net', 'GF Nets']
net_colors = ['Blue', 'White', 'White & Blue']
net_sizes = ['L180xW160xH170.']
funding_source = [
    'Against Malaria Foundation', 'DFID/AMF', 'Global Fund', 'Global Fund (TASO)', 'Global Fund (AMF)',
    'USAID/PMI']
manufacturers = [
    'A to Z Textile Mills Ltd', 'Net Health Ltd', 'Shobikaa Impex Private Ltd',
    'Sumitomo', 'Tana Netting', 'USAID', 'Vestergaard', 'V.K.A Polymers Pvt Ltd']

made_in = ['India', 'Switzerland', 'Tanzania', 'Vietnam']

for i in range(20):
    sheet_name = "Sheet%s" % i

    worksheet = workbook.add_worksheet(sheet_name)

    headings = [
        'PO Number', 'WayBill Number', 'Goods Received Note', 'Manufacturer', 'Entry Date',
        'Quantity Received', 'Remarks', 'Warehouse Name', 'Warehouse Branch', 'Funding Source', 'Net Type',
        'Net Color', 'Net Size', 'UNBS Samples', 'Made In'
    ]

    for idx, title in enumerate(headings):
        worksheet.write(0, idx, title, bold)
    worksheet.data_validation(1, 3, 1000, 3, {'validate': 'list', 'source': manufacturers})
    worksheet.data_validation(1, 7, 1000, 7, {'validate': 'list', 'source': warehouse_list})
    worksheet.data_validation(1, 8, 1000, 8, {'validate': 'list', 'source': warehouse_branches})
    worksheet.data_validation(1, 9, 1000, 9, {'validate': 'list', 'source': funding_source})
    worksheet.data_validation(1, 10, 1000, 10, {'validate': 'list', 'source': net_types})
    worksheet.data_validation(1, 11, 1000, 11, {'validate': 'list', 'source': net_colors})
    worksheet.data_validation(1, 12, 1000, 12, {'validate': 'list', 'source': net_sizes})
    worksheet.data_validation(1, 14, 1000, 14, {'validate': 'list', 'source': made_in})
    worksheet.set_column("A:A", 15, text_format)
    worksheet.set_column("B:C", 30, text_format)
    worksheet.set_column("D:D", 15, text_format)
    worksheet.set_column("B:C", 15, text_format)
    worksheet.set_column("E:F", 18, text_format)
    worksheet.set_column("G:G", 15, date_format)
    worksheet.set_column("H:O", 20, text_format)
    worksheet.write_comment('A1', 'Role should either be VHT, Nurse or Midwife', {'visible': False})
    worksheet.write_comment('E1', 'Entry date should be of the form DD Month YYY.\n eg 20 Nov 2017', {'visible': False})
    worksheet.conditional_format(1, 4, 1000, 4, {
        'type': 'date', 'criteria': 'between', 'minimum': date(2016, 1, 1),
        'maximum': date(2018, 12, 12), 'format': date_format,
    })

workbook.close()

conn.close()
