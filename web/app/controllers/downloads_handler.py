import web
from . import csrf_protected, db, require_login, render
from StringIO import StringIO
import csv


class Downloads:
    @require_login
    def GET(self):
        # params = web.input(d_id="")
        districts = db.query(
            "SELECT id, name FROM locations WHERE type_id = "
            "(SELECT id FROM locationtype WHERE name = 'district') ORDER by name")
        district = {}
        l = locals()
        del l['self']
        return render.downloads(**l)

    @require_login
    def POST(self):
        params = web.input(district=0)
        r = db.query(
            "SELECT district, destination, waybill, quantity_bales, delivered_by, "
            "telephone FROM distribution_log_w2sc_view "
            "WHERE district_id = $district", {'district': params.district})
        csv_file = StringIO()
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['District', 'Total Bales', 'Waybill', 'Qty Bales', 'Driver Name', 'Telephone'])
        for i in r:
            csv_writer.writerow(
                [
                    i['district'], i['destination'], i['waybill'], i['quantity_bales'],
                    i['delivered_by'], i['telephone']])
        web.header('Content-Type', 'text/csv')
        web.header('Content-disposition', 'attachment; filename=DistrictDrivers.csv')
        return csv_file.getvalue()
