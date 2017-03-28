import web
from . import csrf_protected, db, require_login, render
from StringIO import StringIO
import csv


class Downloads:
    @require_login
    def GET(self):
        # params = web.input(d_id="")
        district_SQL = (
            "SELECT id, name FROM locations WHERE type_id = "
            "(SELECT id FROM locationtype WHERE name = 'district') ORDER by name")
        districts = db.query(district_SQL)
        districts1 = db.query(district_SQL)
        district = {}
        l = locals()
        del l['self']
        return render.downloads(**l)

    @require_login
    def POST(self):
        params = web.input(district=0, download="")
        csv_file = StringIO()
        csv_writer = csv.writer(csv_file)
        if params.download == 'Driver':
            r = db.query(
                "SELECT district, destination, waybill, quantity_bales, delivered_by, "
                "telephone FROM distribution_log_w2sc_view "
                "WHERE district_id = $district", {'district': params.district})
            csv_writer.writerow(['District', 'Total Bales', 'Waybill', 'Qty Bales', 'Driver Name', 'Telephone'])
            for i in r:
                csv_writer.writerow(
                    [
                        i['district'], i['destination'], i['waybill'], i['quantity_bales'],
                        i['delivered_by'], i['telephone']])
            filename = "DistrictDrivers.csv"

        elif params.download == 'District Reporters':
            district = ""
            y = db.query(
                "SELECT name FROM locations WHERE id = $district",
                {'district': params.district})
            if y:
                district = y[0]['name']
            SQL = (
                "select initcap(a.firstname) || ' ' || initcap(a.lastname) as name, a.telephone, "
                "a.alternate_tel, a.role, a.email, district, loc_name as reporting_location, b.username "
                "created_by from reporters_view4 a, users b WHERE district_id = $district ")
            r = db.query(SQL, {'district': params.district})
            csv_writer.writerow(
                ['Name', 'Telephone', 'Atl Telephone', 'Role', 'Email', 'District', 'Reporting Location', 'Created By'])
            for i in r:
                csv_writer.writerow(
                    [
                        i['name'], i['telephone'], i['alternate_tel'], i['role'], i['email'],
                        i['district'], i['reporting_location'], i['created_by']])
            filename = '%s-Reporters.csv' % district.capitalize()
        web.header('Content-Type', 'text/csv')
        web.header('Content-disposition', 'attachment; filename=%s' % filename)
        return csv_file.getvalue()
