import web
from . import csrf_protected, db, require_login, render


class Dashboard:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="")
        edit_val = params.ed
        total_nets = db.query("SELECT SUM(quantity_bales) as total FROM national_delivery_log")
        if total_nets:
            total_nets = total_nets[0]
        r = db.query("SELECT SUM(quantity_bales) AS total FROM distribution_log_w2sc_view")
        sc_dist = r[0].total if r else 0
        r = db.query("SELECT count(distinct id) FROM distribution_log_w2sc_view")
        sc_count = r[0].count or 0
        l = locals()
        del l['self']
        return render.dashboard(**l)

    @csrf_protected
    @require_login
    def POST(self):
        params = web.input(page="1", ed="", d_id="")
        try:
            page = int(params.page)
        except:
            page = 1

        with db.transaction():
            if params.ed:
                return web.seeother("/dashboard")
            else:
                return web.seeother("/dashboard")

        l = locals()
        del l['self']
        return render.dashboard(**l)
