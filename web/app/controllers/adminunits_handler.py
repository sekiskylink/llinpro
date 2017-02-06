import web
from . import csrf_protected, db, require_login, render, get_session
from app.tools.utils import audit_log


class AdminUnits:
    @require_login
    def GET(self):
        params = web.input(d_id="", ed="")
        session = get_session()
        districts = db.query(
            "SELECT id, name FROM locations WHERE type_id = "
            "(SELECT id FROM locationtype WHERE name = 'district') ORDER by name")
        district = {}
        allow_edit = False
        try:
            edit_val = int(params.ed)
            allow_edit = True
        except ValueError:
            pass
        if params.ed and allow_edit:
            res = db.query("SELECT name FROM locations WHERE id = $id", {'id': edit_val})
            if res:
                loc = res[0]
                location_name = loc['name']
                print location_name
                ancestors = db.query(
                    "SELECT id, name, level FROM get_ancestors($loc) "
                    "WHERE level > 1 ORDER BY level DESC;", {'loc': edit_val})
                if ancestors:
                    for loc in ancestors:
                        if loc['level'] == 5:
                            village = loc
                        elif loc['level'] == 4:
                            parish = loc
                            villages = db.query("SELECT id, name FROM get_children($id)", {'id': loc['id']})
                        elif loc['level'] == 3:
                            subcounty = loc
                            parishes = db.query("SELECT id, name FROM get_children($id)", {'id': loc['id']})
                        elif loc['level'] == 2:
                            district = loc
                            subcounties = db.query("SELECT id, name FROM get_children($id)", {'id': loc['id']})
                else:
                    district = edit_val
        l = locals()
        del l['self']
        return render.adminunits(**l)

    @csrf_protected
    @require_login
    def POST(self):
        session = get_session()
        params = web.input(ed="", d_id="", location_name="", parish="", location="")
        allow_edit = False
        try:
            edit_val = int(params.ed)
            allow_edit = True
        except:
            pass

        with db.transaction():
            if params.ed and allow_edit:
                r = db.query(
                    "UPDATE locations SET name = $name WHERE id = $id",
                    {'name': params.location_name, 'id': params.location})
                if r:
                    log_dict = {
                        'logtype': 'Web', 'action': 'Edit', 'actor': session.username,
                        'ip': web.ctx['ip'],
                        'descr': 'Edit Village Name (id:%s)=>%s' % (
                            params.location, params.location_name),
                        'user': session.sesid
                    }
                    audit_log(db, log_dict)
                return web.seeother("/adminunits")
            else:  # adding village
                parent = params.parish if params.parish else 0
                village_name = params.location_name
                r = db.query("SELECT add_node(1, $village_name, $parent)", {
                    'village_name': village_name, 'parent': parent})
                if r:
                    log_dict = {
                        'logtype': 'Web', 'action': 'Create', 'actor': session.username,
                        'ip': web.ctx['ip'],
                        'descr': 'Created Village(parent:%s)=>%s' % (
                            parent, village_name),
                        'user': session.sesid
                    }
                    audit_log(db, log_dict)
                return web.seeother("/adminunits")
