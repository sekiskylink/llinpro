import web
from . import csrf_protected, db, require_login, get_session, render
from app.tools.utils import audit_log
import json


class Reporters:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="", caller="web", search="")
        edit_val = params.ed
        session = get_session()
        districts = db.query(
            "SELECT id, name FROM locations WHERE type_id = "
            "(SELECT id FROM locationtype WHERE name = 'district') ORDER by name")
        roles = db.query("SELECT id, name from reporter_groups order by name")
        district = {}
        allow_edit = False
        try:
            edit_val = int(params.ed)
            allow_edit = True
        except ValueError:
            pass
        if params.ed and allow_edit:
            res = db.query(
                "SELECT id, firstname, lastname, telephone, email, national_id, "
                "reporting_location, distribution_point, role, dpoint,alternate_tel "
                "FROM reporters_view "
                " WHERE id = $id", {'id': edit_val})
            if res:
                r = res[0]
                firstname = r.firstname
                lastname = r.lastname
                telephone = r.telephone
                email = r.email
                role = r.role
                national_id = r.national_id
                alt_telephone = r.alternate_tel
                dpoint_id = r.distribution_point
                dpoint = r.dpoint
                location = r.reporting_location
                subcounty = ""
                district = ""
                parish = ""
                village = location
                villages = []
                parishes = []
                subcounties = []
                ancestors = db.query(
                    "SELECT id, name, level FROM get_ancestors($loc) "
                    "WHERE level > 1 ORDER BY level DESC;", {'loc': location})
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
                    district = location
        allow_del = False
        try:
            del_val = int(params.d_id)
            allow_del = True
        except ValueError:
            pass
        if params.d_id and allow_del:
            if session.role in ('Micro Planning', 'Administrator'):
                reporter = db.query(
                    "SELECT firstname || ' ' || lastname as name , telephone "
                    "FROM reporters WHERE id = $id", {'id': params.d_id})
                if reporter:
                    rx = reporter[0]
                    log_dict = {
                        'logtype': 'Web', 'action': 'Delete', 'actor': session.username,
                        'ip': web.ctx['ip'], 'descr': 'Deleted reporter %s:%s (%s)' % (
                            params.d_id, rx['name'], rx['telephone']),
                        'user': session.sesid
                    }
                    db.query("DELETE FROM reporter_groups_reporters WHERE reporter_id=$id", {'id': params.d_id})
                    db.query("DELETE FROM reporters WHERE id=$id", {'id': params.d_id})
                    audit_log(db, log_dict)
                    if params.caller == "api":  # return json if API call
                        web.header("Content-Type", "application/json; charset=utf-8")
                        return json.dumps({'message': "success"})
        if session.role == 'Administrator':
            if params.search:
                REPORTER_SQL = (
                    "SELECT * FROM reporters_view4 WHERE  telephone ilike $search OR "
                    " firstname ilike $search OR lastname ilike $search")
            else:
                REPORTER_SQL = "SELECT * FROM reporters_view4 WHERE id >  (SELECT max(id) - 8 FROM reporters);"
        else:
            if params.search:
                REPORTER_SQL = (
                    "SELECT * FROM reporters_view4 WHERE created_by = $user AND "
                    " (firstname ilike $search OR lastname ilike $search OR telephone ilike $search)")
            else:
                REPORTER_SQL = "SELECT * FROM reporters_view4 WHERE created_by = $user ORDER BY id DESC LIMIT 50"

        reporters = db.query(REPORTER_SQL, {'user': session.sesid, 'search': '%%%s%%' % params.search})
        l = locals()
        del l['self']
        return render.reporters(**l)

    @csrf_protected
    @require_login
    def POST(self):
        session = get_session()
        params = web.input(
            firstname="", lastname="", telephone="", email="", location="", dpoint="",
            national_id="", role="", alt_telephone="", page="1", ed="", d_id="", district="")

        allow_edit = False
        try:
            edit_val = int(params.ed)
            allow_edit = True
        except:
            pass

        with db.transaction():
            if params.ed and allow_edit:
                location = params.location if params.location else None
                dpoint = params.dpoint if params.dpoint else None
                r = db.query(
                    "UPDATE reporters SET firstname=$firstname, lastname=$lastname, "
                    "telephone=$telephone, email=$email, reporting_location=$location, "
                    "distribution_point=$dpoint, national_id=$nid, alternate_tel=$alt_tel, "
                    "district_id = $district_id "
                    "WHERE id=$id RETURNING id", {
                        'firstname': params.firstname, 'lastname': params.lastname,
                        'telephone': params.telephone, 'email': params.email,
                        'location': location, 'dpoint': dpoint, 'nid': params.national_id,
                        'id': params.ed, 'alt_tel': params.alt_telephone, 'district_id': params.district
                    })
                if r:
                    db.query(
                        "UPDATE reporter_groups_reporters SET group_id = $gid "
                        " WHERE reporter_id = $id ", {'gid': params.role, 'id': params.ed})
                    log_dict = {
                        'logtype': 'Web', 'action': 'Update', 'actor': session.username,
                        'ip': web.ctx['ip'],
                        'descr': 'Updated reporter %s:%s (%s)' % (
                            params.ed, params.firstname + ' ' + params.lastname, params.telephone),
                        'user': session.sesid
                    }
                    audit_log(db, log_dict)
                return web.seeother("/reporters")
            else:
                location = params.location if params.location else None
                dpoint = params.dpoint if params.dpoint else None
                has_reporter = db.query(
                    "SELECT id FROM reporters WHERE telephone = $tel", {'tel': params.telephone})
                if has_reporter:
                    session.rdata_err = (
                        "Reporter with Telephone:%s already registered" % params.telephone
                    )
                    return web.seeother("/reporters")
                session.rdata_err = ""
                r = db.query(
                    "INSERT INTO reporters (firstname, lastname, telephone, email, "
                    " reporting_location, distribution_point, national_id, alternate_tel, uuid, "
                    " created_by, district_id) VALUES "
                    " ($firstname, $lastname, $telephone, $email, $location, $dpoint,"
                    " $nid, $alt_tel, uuid_generate_v4(), $user, $district_id) RETURNING id", {
                        'firstname': params.firstname, 'lastname': params.lastname,
                        'telephone': params.telephone, 'email': params.email,
                        'location': location, 'dpoint': dpoint, 'nid': params.national_id,
                        'alt_tel': params.alt_telephone, 'user': session.sesid, 'district_id': params.district
                    })
                if r:
                    reporter_id = r[0]['id']
                    db.query(
                        "INSERT INTO reporter_groups_reporters (group_id, reporter_id) "
                        " VALUES ($role, $reporter_id)",
                        {'role': params.role, 'reporter_id': reporter_id})
                    log_dict = {
                        'logtype': 'Web', 'action': 'Create', 'actor': session.username,
                        'ip': web.ctx['ip'],
                        'descr': 'Created reporter %s:%s (%s)' % (
                            reporter_id, params.firstname + ' ' + params.lastname, params.telephone),
                        'user': session.sesid
                    }
                    audit_log(db, log_dict)
                return web.seeother("/reporters")

        l = locals()
        del l['self']
        return render.reporters(**l)
