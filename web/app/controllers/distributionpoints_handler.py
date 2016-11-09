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
        if params.ed:
            res = db.query(
                "SELECT id, name, subcounty, get_location_name(subcounty) subcounty_name , "
                " get_district(subcounty) district FROM distribution_points "
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

        if params.d_id:
            if session.role in ('Micro Planning', 'Administrator'):
                db.query(
                    "DELETE FROM distribution_point_villages WHERE distribution_point=$id",
                    {'id': params.d_id})
                db.query("DELETE FROM distribution_points WHERE id=$id", {'id': params.d_id})

        dpoints = db.query(
            "SELECT id, name, get_location_name(subcounty) as subcounty, "
            " get_distribution_point_locations(id) villages FROM distribution_points")
        l = locals()
        del l['self']
        return render.dpoints(**l)

    @csrf_protected
    @require_login
    def POST(self):
        params = web.input(
            name="", subcounty="", villages=[], page="1", ed="", d_id="")
        try:
            page = int(params.page)
        except:
            page = 1

        with db.transaction():
            if params.ed:
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
                r = db.query(
                    "INSERT INTO  distribution_points (name, subcounty, uuid, code) "
                    " VALUES ($name, $subcounty, uuid_generate_v4(), gen_code())"
                    " RETURNING id",
                    {'name': params.name, 'subcounty': params.subcounty})
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
