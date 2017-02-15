import web
from . import csrf_protected, db, require_login, render, get_session
from app.tools.utils import audit_log


class Stores:
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
            int(params.ed)
            allow_edit = True
        except ValueError:
            pass
        subcounty = ""
        district = ""
        parish = ""
        village = ""
        villages = []
        parishes = []
        subcounties = []
        if params.ed and allow_edit:
            edit_val = params.ed
            res = db.query("SELECT name, location FROM stores WHERE id = $id", {'id': edit_val})
            if res:
                s = res[0]
                store_name = s['name']
                loc = s['location']
                ancestors = db.query(
                    "SELECT id, name, level FROM get_ancestors($loc) "
                    "WHERE level > 1 ORDER BY level DESC;", {'loc': loc})
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
        if session.role == 'Administrator':
            stores = db.query(
                "SELECT id, name, get_location_name(district_id) district, "
                " get_location_name(location) as location_name FROM stores")
        else:
            stores = db.query(
                "SELECT id, name, get_location_name(district_id) district, "
                "get_location_name(location) location_name FROM stores WHERE created_by = $user",
                {'user': session.sesid})
        l = locals()
        del l['self']
        return render.subcountystores(**l)

    @csrf_protected
    @require_login
    def POST(self):
        session = get_session()
        params = web.input(ed="", d_id="", store_name="", location="", district="")
        allow_edit = False
        try:
            edit_val = int(params.ed)
            allow_edit = True
        except:
            pass

        with db.transaction():
            if params.ed and allow_edit:
                r = db.query(
                    "UPDATE stores SET name = $name, location = $loc, district_id = $district "
                    "WHERE id = $id", {
                        'name': params.store_name, 'id': edit_val,
                        'loc': params.location, 'district': params.district})
                if r:
                    log_dict = {
                        'logtype': 'Web', 'action': 'Edit', 'actor': session.username,
                        'ip': web.ctx['ip'],
                        'descr': 'Edit Store Name (id:%s)=>%s' % (
                            params.location, params.store_name),
                        'user': session.sesid
                    }
                    audit_log(db, log_dict)
                return web.seeother("/stores")
            else:  # adding village
                parent = params.location if params.location else 0
                store_name = params.store_name
                r = db.query(
                    "INSERT INTO stores(name, location, district_id, created_by) "
                    "VALUES ($name, $loc, $district, $user);", {
                        'name': store_name, 'loc': parent,
                        'user': session.sesid, 'district': params.district})
                if r:
                    log_dict = {
                        'logtype': 'Web', 'action': 'Create', 'actor': session.username,
                        'ip': web.ctx['ip'],
                        'descr': 'Created Store (parent:%s)=>%s' % (
                            parent, store_name),
                        'user': session.sesid
                    }
                    audit_log(db, log_dict)
                return web.seeother("/stores")
