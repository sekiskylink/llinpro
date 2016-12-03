import json
from . import db
import web
from app.tools.utils import get_basic_auth_credentials, auth_user, format_msisdn


def get_webhook_msg(params, label='msg'):
    """Returns value of given lable from rapidpro webhook data"""
    values = json.loads(params['values'])  # only way we can get out Rapidpro values in webpy
    msg_list = [v.get('value') for v in values if v.get('label') == label]
    if msg_list:
        msg = msg_list[0].strip()
        if msg.startswith('.'):
            msg = msg[1:]
        return msg
    return ""


class LocationChildren:
    """Returns Children for a node """
    def GET(self, id):
        ret = []
        rs = db.query(
            "SELECT id, name, tree_parent_id FROM get_children($id) ORDER BY name;", {'id': id})
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


class WarehouseBranches:
    def GET(self, id):
        web.header("Content-Type", "application/json; charset=utf-8")
        ret = []
        res = db.query(
            "SELECT id, name FROM warehouse_branches WHERE warehouse_id = $id",
            {'id': id})
        for r in res:
            ret.append({'id': r.id, 'name': r.name})
        return json.dumps(ret)


class FormSerials:
    def POST(self):
        web.header("Content-Type", "application/json; charset=utf-8")
        params = web.input()
        msg = get_webhook_msg(params, 'msg')  # here we get rapidpro value with label msg
        ret = "failed to register form"

        phone = format_msisdn(params.phone.replace(' ', ''))
        phone = phone.replace('+', '')
        r = db.query(
            "SELECT id FROM reporters WHERE replace(telephone, '+', '') = $tel "
            "OR replace(alternate_tel, '+', '') = $tel LIMIT 1", {'tel': phone})
        if r and msg:
            if len(msg) > 6:
                return json.dumps({'message': 'Serial number longer than 6 characters'})
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


class VhtCode:
    def POST(self):
        web.header("Content-Type", "application/json; charset=utf-8")
        params = web.input()
        msg = get_webhook_msg(params, 'msg')  # here we get rapidpro value with label msg
        ret = "failed to record VHT number"
        phone = params.phone.replace('+', '')
        r = db.query(
            "SELECT id FROM reporters WHERE replace(telephone, '+', '') = $tel "
            "OR replace(alternate_tel, '+', '') = $tel LIMIT 1", {'tel': phone})
        if r and msg:
            reporter_id = r[0].id

            if len(msg) > 2:
                return json.dumps({'message': 'VHT number longer than 2 characters'})
            db.query("UPDATE reporters SET code = $code WHERE id = $id", {'code': msg, 'id': reporter_id})
            ret = "you have been recorded as VHT: %s" % msg
        return json.dumps({"message": ret})


class SerialsEndpoint:
    def GET(self, subcount_code):
        params = web.input(from_date="")
        web.header("Content-Type", "application/json; charset=utf-8")
        username, password = get_basic_auth_credentials()
        r = auth_user(db, username, password)
        if not r[0]:
            web.header('WWW-Authenticate', 'Basic realm="Auth API"')
            web.ctx.status = '401 Unauthorized'
            return json.dumps({'detail': 'Authentication failed!'})

        y = db.query("SELECT id FROM locations WHERE code = $code", {'code': subcount_code})
        location_id = 0
        if y:
            location_id = y[0]['id']

        SQL = (
            "SELECT firstname, lastname, telephone, uuid, reporter_code, location_name, "
            "location_code, location_uuid, form_serial, location_id, email, created "
            " FROM registration_forms_view WHERE (location_id = $id "
            " OR location_id IN (SELECT id FROM get_descendants($id))) ")
        if params.from_date:
            SQL += " AND cdate >= $date "
        r = db.query(SQL, {'id': location_id, 'date': params.from_date})
        ret = []
        for i in r:
            ret.append(dict(i))
        return json.dumps(ret)


class WarehouseRecord:
    def GET(self, id):
        r = db.query(
            "SELECT po_number, made_in, funding_source_name, manufacturer_name, nets_type, nets_color, "
            "nets_size, waybill, goods_received_note, warehouse, branch_name, sub_warehouse, "
            "quantity_bales, quantity, entry_date, "
            "nda_samples, nda_sampling_date, nda_conditional_release_date, nda_testing_result_date, "
            "unbs_samples, unbs_sampling_date, remarks FROM national_delivery_log_view WHERE id = $id", {'id': id})
        ret = {}
        html_str = '<table class="table table-striped table-bordered table-hover">'
        html_str += "<thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>"
        if r:
            ret = r[0]
            html_str += "<tr><td>PO Number</td><td>%s</td></tr>" % ret['po_number']
            html_str += "<tr><td>Funding Source</td><td>%s</td></tr>" % ret['funding_source_name']
            html_str += "<tr><td>Manufacturer</td><td>%s</td></tr>" % (ret['manufacturer_name'] + " (" + ret['made_in'] + ")")
            html_str += "<tr><td>Net Info</td><td>%s</td></tr>" % (
                "Type: " + ret['nets_type'] + ", Color: " + ret['nets_color'] + ", Size: " + ret['nets_size'])
            html_str += "<tr><td>Waybill</td><td>Waybill: %s, GRN: %s</td></tr>" % (
                ret['waybill'], ret['goods_received_note'])
            # html_str += "<tr><td>Good Received Note</td><td>%s</td></tr>" % ret['goods_received_note']
            html_str += "<tr><td>Quantity</td><td>%s</td></tr>" % (
                "Bales: " + str(ret['quantity_bales']) + ", Nets: " + str(ret['quantity']))
            html_str += "<tr><td>Warehouse</td><td>%s</td></tr>" % (
                ret['warehouse'] + " - (" + ret['branch_name'] + ") => " + ret['sub_warehouse'])
            html_str += "<tr><td>Entry Date</td><td>%s</td></tr>" % (ret['entry_date'])
            html_str += "<tr><td>UNBS </td><td>Samples: %s, Sampling Date: %s</td></tr>" % (
                ret['unbs_samples'], ret['unbs_sampling_date'])
            html_str += "<tr><td>NDA </td><td>Samples: %s, Sampling Date: %s</td></tr>" % (
                ret['nda_samples'], ret['nda_sampling_date'])
            html_str += "<tr><td>NDA Cond. Release Date</td><td>%s</td></tr>" % (ret['nda_conditional_release_date'])
            html_str += "<tr><td>NDA Testing Result Date</td><td>%s</td></tr>" % (ret['nda_testing_result_date'])
            html_str += "<tr><td>Remarks</td><td>%s</td></tr>" % (ret['remarks'])
        html_str += "</tbody></table>"

        return html_str


class DistributionRecord:
    def GET(self, id):
        r = db.query("SELECT * FROM distribution_log_w2sc_view WHERE id = $id", {'id': id})
        html_str = '<table class="table table-striped table-bordered table-hover">'
        html_str += "<thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>"
        if r:
            ret = r[0]
            html_str += "<tr><td>District</td><td>%s</td></tr>" % ret['district']
            html_str += "<tr><td>Sub County</td><td>%s</td></tr>" % ret['destination']
            html_str += "<tr><td>Release Order</td><td>%s</td></tr>" % ret['release_order']
            html_str += "<tr><td>Waybill</td><td>%s</td></tr>" % ret['waybill']
            html_str += "<tr><td>Quantity</td><td>Bales: %s, Nets: %s</td></tr>" % (ret['quantity_bales'], ret['quantity_nets'])
            html_str += "<tr><td>Warehouse</td><td>%s (%s)</td></tr>" % (ret['warehouse'], ret['branch'])
            html_str += "<tr><td>Departure Date</td><td>%s</td></tr>" % ret['departure_date']
            html_str += "<tr><td>Departure Time</td><td>%s</td></tr>" % ret['departure_time']
            html_str += "<tr><td>Quantity Received</td><td>%s</td></tr>" % ret['quantity_received']
            html_str += "<tr><td>Driver</td><td>Name: %s, Tel:%s</td></tr>" % (ret['delivered_by'], ret['telephone'])
            html_str += "<tr><td>Remarks</td><td>%s</td></tr>" % ret['remarks']
            if ret['is_delivered']:
                label = "<span class='label label-primary'>Delivered</span>"
                html_str += "<tr><td>Delivered?</td><td>%s</td></tr>" % label
            else:
                label = "<span class='label label-danger'>Not Delivered</span>"
                html_str += "<tr><td>Delivered?</td><td>%s</td></tr>" % label
        html_str += "</tbody></table>"
        return html_str
