import json
from . import db
import web


class LocationChildren:
    """Returns Children for a node """
    def GET(self, id):
        ret = []
        rs = db.query(
            "SELECT id, name, tree_parent_id FROM get_children($id);", {'id': id})
        if rs:
            for r in rs:
                parent = r['tree_parent_id']
                ret.append(
                    {
                        "name": r['name'],
                        "id": r['id'],
                        "attr": {'id': r['id']},
                        "parent": parent if parent else "#",
                        "state": "closed"
                    })
        return json.dumps(ret)


class Location:
    def GET(self, id):
        ret = []
        rs = db.query(
            "SELECT id, name, tree_parent_id FROM locations WHERE id = $id;", {'id': id})
        if rs:
            for r in rs:
                parent = r['tree_parent_id']
                ret.append(
                    {
                        "text": r['name'],
                        "attr": {'id': r['id']},
                        "id": parent if parent else "#",
                        "state": "closed"
                    })
        return json.dumps(ret)


class DistributionPoints:
    """Returns Distribution Points in Sub County"""
    def GET(self, id):
        ret = []
        rs = db.query(
            "SELECT id, name, code, uuid FROM distribution_points "
            "WHERE subcounty = $id;", {'id': id})
        if rs:
            for r in rs:
                ret.append(
                    {
                        "id": r['id'],
                        "name": r['name'],
                        "uuid": r['uuid'],
                        "code": r['code'],
                    })
        return json.dumps(ret)


class SubcountyLocations:
    def GET(self, id):
        """ returs the form bellow
        ret = {
            "Parish X": [{'name': "Villa 1"}, {"name": "Villa 2"}, {"name": "Villa 3"}],
            "Parish Y": [{'name': "Villa 4"}, {"name": "Villa 5"}],
            "Parish Z": [{'name': "Villa 6"}, {"name": "Villa 7"}],
        }
        """
        web.header("Content-Type", "application/json; charset=utf-8")
        ret = {}
        res = db.query("SELECT id, name FROM get_children($id)", {'id': id})
        for r in res:
            parish_name = r['name']
            parish_id = r['id']
            ret[parish_name] = []
            x = db.query("SELECT id, name FROM get_children($id)", {'id': parish_id})
            for i in x:
                ret[parish_name].append({'id': i['id'], 'name': i['name']})
        return json.dumps(ret)


class FormSerials:
    def POST(self):
        web.header("Content-Type", "application/json; charset=utf-8")
        params = web.input()
        values = json.loads(params['values'])  # only way we can get out Rapidpro values in webpy
        msg_list = [v.get('value') for v in values if v.get('label') == 'msg']
        ret = "failed to register form"
        if msg_list:
            msg = msg_list[0]
            if msg.startswith('.'):
                msg = msg[1:]
            phone = params.phone.replace('+', '')
            r = db.query(
                "SELECT id FROM reporters WHERE telephone = $tel "
                "OR alternate_tel = $tel LIMIT 1", {'tel': phone})
            if r and msg:
                reporter_id = r[0].id
                # check if form serial not captured yet
                res = db.query("SELECT id FROM registration_forms WHERE serial_number = $serial", {'serial': msg})
                if not res:
                    db.query(
                        "INSERT INTO registration_forms (reporter_id, serial_number) "
                        "VALUES ($reporter, $form) ", {'reporter': reporter_id, 'form': msg})
                    ret = "registration form with serial: %s successfully recorded" % msg
                else:
                    ret = "registration form with serial: %s already registered" % msg
        return json.dumps({"message": ret})


class SerialsEndpoint:
    def GET(self, subcount_code):
        params = web.input(from_date="")
        web.header("Content-Type", "application/json; charset=utf-8")
        y = db.query("SELECT id FROM locations WHERE code = $code", {'code': subcount_code})
        location_id = 0
        if y:
            location_id = y[0]['id']

        # r = db.query("SELECT * FROM registration_forms_view WHERE location_code = $code", {'code': subcount_code})
        print location_id
        SQL = (
            "SELECT * FROM registration_forms_view WHERE location_id = $id "
            " OR location_id IN (SELECT id FROM get_descendants($id)) ")
        if params.from_date:
            SQL += " AND created >= $date "
        r = db.query(SQL, {'id': location_id, 'date': params.from_date})
        ret = []
        for i in r:
            ret.append(dict(i))
        return json.dumps(ret)
