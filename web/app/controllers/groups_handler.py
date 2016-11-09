import web
from . import csrf_protected, db, require_login, render


class Groups:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="")
        edit_val = params.ed
        groups = db.query("SELECT id, name, descr FROM user_roles order by id desc")
        l = locals()
        del l['self']
        return render.groups(**l)

    @csrf_protected
    @require_login
    def POST(self):
        params = web.input(
            name="", descr="", page="1", ed="", d_id="")
        try:
            page = int(params.page)
        except:
            page = 1

        with db.transaction():
            if params.ed:
                pass
                return web.seeother("/groups")
            else:
                r = db.query(
                    "INSERT INTO user_roles (name, descr) "
                    " VALUES ($name, $descr)",
                    {'name': params.name, 'descr': params.descr})
                return web.seeother("/groups")

        l = locals()
        del l['self']
        return render.reporters(**l)
