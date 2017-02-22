import web
from . import csrf_protected, db, require_login, render


class Hotline:
    @require_login
    def GET(self):
        # params = web.input(d_id="")
        alerts = db.query(
            "SELECT id, get_location_name(district_id) district,  "
            "get_location_name(reporting_location) loc_name, alert "
            "FROM alerts ORDER BY ID DESC LIMIT 700")
        l = locals()
        del l['self']
        return render.hotline(**l)
