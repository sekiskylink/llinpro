import web
from . import csrf_protected, db, require_login, render, get_session


class DistPoints:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="")
        edit_val = params.ed
        session = get_session()
        districts = db.query(
            "SELECT id, name FROM locations WHERE type_id = "
            "(SELECT id FROM locationtype WHERE name = 'district') ORDER by name")
        allow_edit = False
        try:
            edit_val = int(params.ed)
            allow_edit = True
        except ValueError:
            pass
        if params.ed and allow_edit:
            res = db.query(
                "SELECT id, name, subcounty, get_location_name(subcounty) subcounty_name , "
                " get_location_name(district_id) district FROM distribution_points "
                " WHERE id = $id", {'id': edit_val})
            if res:
                r = res[0]
                district = r.district
                subcounty = r.subcounty
                subcounty_name = r.subcounty_name
                name = r.name
                villages = db.query(
                    "SELECT id, name FROM locations WHERE id IN "
                    "(SELECT village_id FROM distribution_point_villages "
                    " WHERE distribution_point = $id)", {'id': params.ed})

        allow_del = False
        try:
            del_val = int(params.d_id)
            allow_del = True
        except ValueError:
            pass
        if params.d_id and allow_del:
            if session.role in ('Micro Planning', 'Administrator'):
                db.query(
                    "DELETE FROM distribution_point_villages WHERE distribution_point=$id",
                    {'id': params.d_id})
                db.query("DELETE FROM distribution_points WHERE id=$id", {'id': params.d_id})

        if session.role == 'Administrator':
            dpoints_SQL = (
                "SELECT id, name, get_location_name(subcounty) as subcounty, "
                " get_location_name(district_id) as district, "
                " get_distribution_point_locations(id) villages FROM distribution_points "
                " ORDER by id DESC")
        else:
            dpoints_SQL = (
                "SELECT id, name, get_location_name(subcounty) as subcounty, "
                " get_location_name(district_id) as district, "
                " get_distribution_point_locations(id) villages FROM distribution_points"
                " WHERE created_by = $user ORDER BY id DESC")

        dpoints = db.query(dpoints_SQL, {'user': session.sesid})
        l = locals()
        del l['self']
        return render.dpoints(**l)

    @csrf_protected
    @require_login
    def POST(self):
        session = get_session()
        params = web.input(
            name="", subcounty="", villages=[], page="1", ed="", d_id="")
        allow_edit = False
        try:
            edit_val = int(params.ed)
            allow_edit = True
        except:
            pass

        with db.transaction():
            if params.ed and allow_edit:
                db.query(
                    "DELETE FROM distribution_point_villages WHERE distribution_point=$id",
                    {'id': params.ed})
                db.query(
                    "UPDATE distribution_points SET "
                    " subcounty = $subcounty, name = $name "
                    " WHERE id = $id",
                    {'subcounty': params.subcounty, 'name': params.name, 'id': params.ed})
                for val in params.villages:
                    db.query(
                        "INSERT INTO distribution_point_villages (distribution_point, village_id) "
                        " VALUES($dpoint, $village)", {'dpoint': params.ed, 'village': val})
                return web.seeother("/distributionpoints")
            else:
                has_dp = db.query(
                    "SELECT a.id, b.name  FROM distribution_points a, locations b "
                    "WHERE a.name = $name AND a.subcounty = $subcounty "
                    "AND b.id = a.subcounty", {'name': params.name, 'subcounty': params.subcounty})
                if has_dp:
                    session.dp_err = (
                        "Distribution Points %s of %s subcounty "
                        "already added!" % (params.name, has_dp[0]['name']))
                    return web.seeother("/distributionpoints")
                session.dp_err = ""
                r = db.query(
                    "INSERT INTO  distribution_points (name, subcounty, district_id, uuid, code, created_by) "
                    " VALUES ($name, $subcounty, $district, uuid_generate_v4(), gen_code(), $user)"
                    " RETURNING id", {
                        'name': params.name, 'subcounty': params.subcounty,
                        'district': params.district, 'user': session.sesid})
                if r:
                    dpoint_id = r[0]['id']
                    for val in params.villages:
                        db.query(
                            "INSERT INTO distribution_point_villages (distribution_point, village_id) "
                            " VALUES($dpoint, $village)", {'dpoint': dpoint_id, 'village': val})
                return web.seeother("/distributionpoints")

        l = locals()
        del l['self']
        return render.reporters(**l)
