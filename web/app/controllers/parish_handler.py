import web
from . import csrf_protected, db, require_login, render, get_session
from app.tools.utils import audit_log


class Parish:
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
        try:
            del_val = int(params.d_id)
            allow_del = True
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
                        if loc['level'] == 2:
                            district = loc
                            subcounties = db.query("SELECT id, name FROM get_children($id)", {'id': loc['id']})
                        elif loc['level'] == 3:
                            subcounty = loc
                            parishes = db.query("SELECT id, name FROM get_children($id)", {'id': loc['id']})
                else:
                    district = edit_val
        if params.d_id and allow_del and session.role in ('Administrator', 'Data Manager'):
            print "You seriously want to delete?"
            rs = db.query("select id from get_children($id);", {'id': params.d_id})
            for r in rs:
                try:
                    db.query("SELECT delete_node(1, $id)", {'id': r['id']})
                except:
                    pass
            try:
                db.query("SELECT delete_node(1, $id)", {'id': params.d_id})
            except:
                print "Failed to Delete Node"

        l = locals()
        del l['self']
        return render.parishes(**l)

    @csrf_protected
    @require_login
    def POST(self):
        session = get_session()
        params = web.input(ed="", d_id="", location_name="", subcounty="", location="", district=0)
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
                    {'name': params.location_name, 'id': edit_val})
                if r:
                    log_dict = {
                        'logtype': 'Web', 'action': 'Edit', 'actor': session.username,
                        'ip': web.ctx['ip'],
                        'descr': 'Edit Subcounty Name (id:%s)=>%s' % (
                            params.location, params.location_name),
                        'user': session.sesid
                    }
                    audit_log(db, log_dict)
                return web.seeother("/parishes")
            else:  # adding subcounty
                parent = params.subcounty if params.subcounty else 0
                location_name = params.location_name
                r = db.query("SELECT add_node(1, $location_name, $parent)", {
                    'location_name': location_name, 'parent': parent})
                if r:
                    log_dict = {
                        'logtype': 'Web', 'action': 'Create', 'actor': session.username,
                        'ip': web.ctx['ip'],
                        'descr': 'Created Parish(parent:%s)=>%s' % (
                            parent, location_name),
                        'user': session.sesid
                    }
                    audit_log(db, log_dict)
                return web.seeother("/parishes")
