import json
from . import db
import web
from settings import config, SMS_OFFSET_TIME
from app.tools.utils import get_basic_auth_credentials, auth_user, format_msisdn
from app.tools.utils import get_location_role_reporters, queue_schedule, log_schedule, update_queued_sms
import datetime


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
    def GET(self, subcounty_code):
        params = web.input(from_date="")
        web.header("Content-Type", "application/json; charset=utf-8")
        username, password = get_basic_auth_credentials()
        r = auth_user(db, username, password)
        if not r[0]:
            web.header('WWW-Authenticate', 'Basic realm="Auth API"')
            web.ctx.status = '401 Unauthorized'
            return json.dumps({'detail': 'Authentication failed!'})

        y = db.query("SELECT id FROM locations WHERE code = $code", {'code': subcounty_code})
        location_id = 0
        if y:
            location_id = y[0]['id']

        SQL = (
            "SELECT firstname, lastname, telephone, uuid as reporter_uuid, reporter_code, "
            "location_name, location_code, location_uuid, form_serial, location_id, email, created "
            " FROM registration_forms_view WHERE (location_id = $id "
            " OR location_id IN (SELECT id FROM get_descendants($id))) ")
        if params.from_date:
            SQL += " AND cdate >= $date "
        r = db.query(SQL, {'id': location_id, 'date': params.from_date})
        ret = []
        for i in r:
            ret.append(dict(i))
        return json.dumps(ret)


class DistributionPointsEndpoint:
    def GET(self, subcounty_code):
        # params = web.input()
        web.header("Content-Type", "application/json; charset=utf-8")
        username, password = get_basic_auth_credentials()
        r = auth_user(db, username, password)
        if not r[0]:
            web.header('WWW-Authenticate', 'Basic realm="Auth API"')
            web.ctx.status = '401 Unauthorized'
            return json.dumps({'detail': 'Authentication failed!'})
        ret = []
        rs = db.query(
            "SELECT a.id, a.name, a.code, a.uuid, b.code as subcounty_code FROM "
            " distribution_points a, locations b "
            " WHERE a.subcounty = b.id AND b.code = $code ", {'code': subcounty_code})
        if rs:
            for r in rs:
                villages_sql = (
                    "SELECT b.code, b.name FROM distribution_point_villages a, locations b "
                    "WHERE a.distribution_point = %s AND a.village_id = b.id" % r['id'])
                dpoint_dict = {
                    "id": r['id'],
                    "name": r['name'],
                    "uuid": r['uuid'],
                    "code": r['code'],
                    "villages": []
                }
                res = db.query(villages_sql)
                for l in res:
                    dpoint_dict["villages"].append({'name': l.name, 'code': l.code})

                ret.append(dpoint_dict)
        return json.dumps(ret)


class ReportersEndpoint:
    def GET(self, location_code):
        params = web.input(role="")
        web.header("Content-Type", "application/json; charset=utf-8")
        username, password = get_basic_auth_credentials()
        r = auth_user(db, username, password)
        if not r[0]:
            web.header('WWW-Authenticate', 'Basic realm="Auth API"')
            web.ctx.status = '401 Unauthorized'
            return json.dumps({'detail': 'Authentication failed!'})
        ret = []
        reporter_role = params.role
        SQL = (
            "SELECT firstname, lastname, telephone, alternate_tel, email, national_id, "
            "reporting_location, district, role, loc_name, location_code FROM reporters_view4 "
            "WHERE reporting_location IN (SELECT id FROM get_descendants_including_self(( SELECT id FROM "
            "locations WHERE code=$location_code))) ")
        if reporter_role:
            SQL += " AND lower(role) = $role"
        res = db.query(SQL, {'location_code': location_code, 'role': reporter_role.lower()})
        if res:
            for r in res:
                ret.append({
                    "firstname": r.firstname, "lastname": r.lastname,
                    "telephone": r.telephone, "alternate_tel": r.alternate_tel,
                    "email": r.email, "national_id": r.national_id,
                    "location_name": r.loc_name,
                    "location_code": r.location_code,
                    "distrcit": r.district, "role": r.role
                })
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


class DeliverNets:
    """Webhook for the drivers upon delivery of nets. 'DEL WAYBILL QTY'"""
    def POST(self):
        web.header("Content-Type", "application/json; charset=utf-8")
        params = web.input()
        waybill = get_webhook_msg(params, 'waybill')
        quantity_bales = get_webhook_msg(params, 'quantity_bales')
        try:
            quantity_bales = int(float(quantity_bales))
        except:
            return json.dumps({"message": "The quantity of bales must be a number"})

        phone = params.phone.replace('+', '')
        # print "WAYBILL:%s.::.QTY:%s.::.%s" % (waybill, quantity_bales, phone)
        with db.transaction():
            r = db.query(
                "SELECT id FROM reporters WHERE replace(telephone, '+', '') = $tel "
                "OR replace(alternate_tel, '+', '') = $tel LIMIT 1", {'tel': phone})
            if r and waybill and quantity_bales:
                reporter_id = r[0]['id']
                res = db.query(
                    "UPDATE distribution_log SET is_delivered='t',arrival_date=NOW(), "
                    "arrival_time=current_time  WHERE delivered_by=$driver_id AND source='national' "
                    "AND dest='subcounty' AND waybill=$waybill RETURNING id, quantity_bales", {
                        'driver_id': reporter_id, 'waybill': waybill})
                if res:
                    log = res[0]
                    log_id = log['id']
                    sent_nets = log['quantity_bales']
                    if quantity_bales != sent_nets:
                        db.query(
                            "UPDATE distribution_log SET has_variance='t', updated=now() "
                            "WHERE id = $log_id ", {'log_id': log_id})
                        ret = (
                            "You delivered %s bales of nets with waybill %s. "
                            "Expected value is %s bales. Please resend if "
                            "there is an error" % (quantity_bales, waybill, sent_nets))
                        return json.dumps({"message": ret})
                    else:
                        ret = (
                            "Delivery of %s bales of nets with waybill %s "
                            "successfully recorded." % (quantity_bales, waybill))
                        return json.dumps({"message": ret})
        ret = "Waybill %s not recorgnized. Please resend if there is an error" % (waybill)

        return json.dumps({"message": ret})


class ReceiveNets:
    """This is the webhook used by subcounty store managers upon receipt of nets
    Essentially: (can be used by subcounty store managers, subcounty chiefs or LC3s)
    It tries to add anti-spamming capabilities by relying on the SMS_OFFSET_TIME used
    for scheduling notifications. Each time someone sends in 'REC WAYBILL QTY', a check
    is made for an existing ready schedule on the same waybill from that subcounty.
    If it does exist, then it is updated otherwise created.
    Would NOT SPAM even if different reporters report the REC WAYBILL QTY message
    """
    def POST(self):
        web.header("Content-Type", "application/json; charset=utf-8")
        params = web.input()
        waybill = get_webhook_msg(params, 'waybill')
        quantity_bales = get_webhook_msg(params, 'quantity_bales')
        try:
            quantity_bales = int(float(quantity_bales))
        except:
            return json.dumps({"message": "The quantity of bales must be a number"})

        phone = params.phone.replace('+', '')
        # print "WAYBILL:%s.::.QTY:%s.::.%s" % (waybill, quantity_bales, phone)
        with db.transaction():
            r = db.query(
                "SELECT id, reporting_location, district_id, "
                "district, loc_name subcounty "
                "FROM reporters_view4 WHERE replace(telephone, '+', '') = $tel "
                "OR replace(alternate_tel, '+', '') = $tel LIMIT 1", {'tel': phone})
            if r and waybill and quantity_bales:
                reporter = r[0]
                reporter_id = reporter['id']
                dest_location = reporter['reporting_location']  # subcounty_id
                district_id = reporter['district_id']
                district = reporter['district']
                subcounty = reporter['subcounty']
                res = db.query(
                    "UPDATE distribution_log SET received_by=$reporter, "
                    "is_received = 't', quantity_received=$qty "
                    "WHERE source='national' AND dest='subcounty' AND "
                    "destination=$dest AND waybill=$waybill RETURNING id, quantity_bales", {
                        'reporter': reporter_id, 'qty': quantity_bales,
                        'waybill': waybill, 'dest': dest_location})
                if res:
                    log = res[0]
                    log_id = log['id']
                    sent_nets = log['quantity_bales']

                    # sched_time = time to send SMS
                    current_time = datetime.datetime.now()
                    sched_time = current_time + datetime.timedelta(minutes=SMS_OFFSET_TIME)
                    sms_args = {
                        'subcounty': subcounty,
                        'district': district,
                        'waybill': waybill,
                        'quantity': quantity_bales,
                        'shortcode': config.get('shortcode', '6400')
                    }
                    district_reporters = get_location_role_reporters(
                        db, district_id, config['district_reporters'])
                    district_reporters += get_location_role_reporters(
                        db, dest_location, ['Subcounty Supervisor'])
                    national_reporters = get_location_role_reporters(
                        db, 1, config['national_reporters'])

                    scheduled_msgs = db.query(
                        "SELECT a.schedule_id, a.level, a.triggered_by FROM distribution_log_schedules a, "
                        " schedules b WHERE a.distribution_log_id = $log_id AND "
                        " b.id = a.schedule_id AND b.status = 'ready' "
                        " AND a.triggered_by = $subcounty_id", {
                            'log_id': log_id, 'subcounty_id': dest_location})

                    if quantity_bales != sent_nets:
                        db.query(
                            "UPDATE distribution_log SET has_variance='t', updated=now() "
                            "WHERE id = $log_id ", {'log_id': log_id})
                        ret = (
                            "You received %s bales of nets with waybill %s. "
                            "Expected value is %s bales. Please resend if "
                            "there is an error" % (quantity_bales, waybill, sent_nets))
                        # XXX may notfy some parties
                        if scheduled_msgs:
                            for s in scheduled_msgs:
                                db.query(
                                    "SELECT id FROM schedules WHERE id = $sched_id "
                                    "FOR UPDATE NOWAIT", {'sched_id': s['schedule_id']})

                                # build SMS to send to notifying parties
                                sms_text = config['receive_subcounty_nets_sms_template'] % sms_args
                                if s['level'] == 'national':
                                    sms_params = {'text': sms_text, 'to': ' '.join(national_reporters)}
                                    update_queued_sms(db, s['schedule_id'], sms_params, sched_time)

                                elif s['level'] == 'district':
                                    sms_params = {'text': sms_text, 'to': ' '.join(district_reporters)}
                                    update_queued_sms(db, s['schedule_id'], sms_params, sched_time)

                        else:
                            sms_text = config['receive_subcounty_nets_sms_template'] % sms_args
                            sms_params = {'text': sms_text, 'to': ' '.join(district_reporters)}
                            sched_id = queue_schedule(db, sms_params, sched_time)
                            log_schedule(db, log_id, sched_id, 'district', triggered_by=dest_location)

                            sms_params = {'text': sms_text, 'to': ' '.join(national_reporters)}
                            sched_id = queue_schedule(db, sms_params, sched_time)
                            log_schedule(db, log_id, sched_id, 'national', dest_location)

                        return json.dumps({"message": ret})
                    else:
                        db.query(
                            "UPDATE distribution_log SET has_variance='f', updated=now() "
                            "WHERE id = $log_id ", {'log_id': log_id})
                        ret = (
                            "Receipt of %s bales of nets with waybill %s "
                            "acknowledged." % (quantity_bales, waybill))
                        if scheduled_msgs:
                            for s in scheduled_msgs:
                                db.query(
                                    "SELECT id FROM schedules WHERE id = $sched_id "
                                    "FOR UPDATE NOWAIT", {'sched_id': s['schedule_id']})

                                # build SMS to send to notifying parties
                                sms_text = config['receive_subcounty_nets_sms_template'] % sms_args
                                if s['level'] == 'national':
                                    if national_reporters:
                                        sms_params = {'text': sms_text, 'to': ' '.join(national_reporters)}
                                        update_queued_sms(db, s['schedule_id'], sms_params, sched_time)

                                elif s['level'] == 'district':
                                    if district_reporters:
                                        sms_params = {'text': sms_text, 'to': ' '.join(district_reporters)}
                                        update_queued_sms(db, s['schedule_id'], sms_params, sched_time)
                        else:
                            sms_text = config['receive_subcounty_nets_sms_template'] % sms_args
                            if district_reporters:
                                sms_params = {'text': sms_text, 'to': ' '.join(district_reporters)}
                                sched_id = queue_schedule(db, sms_params, sched_time)
                                log_schedule(db, log_id, sched_id, 'district', triggered_by=dest_location)
                            if national_reporters:
                                sms_params = {'text': sms_text, 'to': ' '.join(national_reporters)}
                                sched_id = queue_schedule(db, sms_params, sched_time)
                                log_schedule(db, log_id, sched_id, 'national', dest_location)

                        return json.dumps({"message": ret})
                else:
                    ret = ("No distribution to your subcounty with waybill: %s " % waybill)
                    return json.dumps({"message": ret})
            else:
                ret = "Waybill %s not recorgnized. Please resend if there is an error" % (waybill)
        return json.dumps({"message": ret})


class DistributeVillageNets:
    """Webhook issued when subcounty store managers distribute to the distribution points"""
    def POST(self):
        web.header("Content-Type", "application/json; charset=utf-8")
        params = web.input()
        waybill = get_webhook_msg(params, 'waybill')
        nets = get_webhook_msg(params, 'quantity_nets')
        try:
            nets = int(float(nets))
        except:
            return json.dumps({"message": "The nets distributed must be a number"})

        phone = params.phone.replace('+', '')
        with db.transaction():
            r = db.query(
                "SELECT id, reporting_location, district_id FROM reporters WHERE replace(telephone, '+', '') = $tel "
                "OR replace(alternate_tel, '+', '') = $tel LIMIT 1", {'tel': phone})
            if r and waybill and nets:
                reporter = r[0]
                reporter_id = reporter['id']
                district_id = reporter['district_id']
                res = db.query(
                    "SELECT id FROM distribution_log_sc2dp_view WHERE waybill = $waybill AND "
                    "reporter_id = $reporter_id", {'waybill': waybill, 'reporter_id': reporter_id})
                if res:
                    # entry already exists
                    log_id = res[0]['id']
                    db.query(
                        "UPDATE distribution_log SET quantity_nets = $nets, updated = now() "
                        "WHERE id = $id", {'nets': nets, 'id': log_id})
                    ret = (
                        "Distribution with Delivery Note No.: %s already recorded by you. "
                        " %s nets have been recorded. If there's an error, please resend." % (waybill, nets))
                    return json.dumps({"message": ret})
                else:
                    dres = db.query(
                        "INSERT INTO distribution_log (source, dest, waybill, quantity_nets, "
                        "delivered_by, departure_date, departure_time, district_id) VALUES ("
                        "'subcounty', 'dp', $waybill, $nets, $reporter_id, current_date, "
                        "current_time, $district_id) RETURNING id", {
                            'waybill': waybill,
                            'reporter_id': reporter_id,
                            'nets': nets, 'district_id': district_id})
                    if dres:
                        # log_id = dres[0]['id']
                        ret = (
                            "Distribution of %s nets with Delivery Note No. %s successfully recorded. "
                            " VHTs will have to confirm receipt of these nets."
                            " If there's an error, please resend" % (nets, waybill))
                        return json.dumps({"message": ret})
            else:
                ret = "Your phone(%s) is not registered in the system." % phone
            return json.dumps({"message": ret})


class ReceiveVillageNets:
    def POST(self):
        web.header("Content-Type", "application/json; charset=utf-8")
        params = web.input()
        waybill = get_webhook_msg(params, 'waybill')
        qty_nets = get_webhook_msg(params, 'quantity_nets')
        try:
            qty_nets = int(float(qty_nets))
        except:
            return json.dumps({"message": "The nets received must be a number"})

        phone = params.phone.replace('+', '')
        with db.transaction():
            r = db.query(
                "SELECT id, reporting_location, district_id, "
                "district, loc_name village "
                "FROM reporters_view4 WHERE replace(telephone, '+', '') = $tel "
                "OR replace(alternate_tel, '+', '') = $tel LIMIT 1", {'tel': phone})
            if r and waybill and qty_nets:
                reporter = r[0]
                district_id = reporter["district_id"]
                district = reporter["district"]
                reporter_id = reporter['id']
                reporting_location = reporter['reporting_location']
                village = reporter['village']
                res = db.query(
                    "SELECT id, quantity_nets, subcounty,  get_location_name(subcounty) subcounty_name FROM "
                    "distribution_log_sc2dp_view WHERE waybill = $waybill AND "
                    "subcounty = (SELECT id FROM get_ancestors($loc) WHERE type_id = 4)",
                    {'waybill': waybill, 'loc': reporting_location})
                if res:
                    # waybill found for that subcounty
                    log = res[0]
                    log_id = log['id']
                    subcounty = log['subcounty']
                    subcounty_name = log['subcounty_name']
                    total_nets = log['quantity_nets']  # total nets at distribution point
                    if qty_nets > total_nets:
                        ret = (
                            "The number of nets(%s) is bigger than the total nets (%s) "
                            "that were sent to distribution point. "
                            "Please resend if there's an error." % (qty_nets, total_nets))
                        return json.dumps({"message": ret})

                    rz = db.query(
                        "SELECT CASE WHEN (sum(quantity_received) > 0) THEN "
                        " sum(quantity_received) ELSE 0 END as total FROM village_distribution_log "
                        "WHERE distribution_log_id = $log_id AND village_id != $village_id", {
                            'log_id': log_id, 'village_id': reporting_location})

                    total_less_for_village = rz[0]["total"]
                    if (total_less_for_village + qty_nets) > total_nets:
                        ret = (
                            "The number of nets (%s) plus that of other villages "
                            " will be more than what was received at the distribution point (%s)."
                            "If there is an error, plese resend" % (qty_nets, total_nets)
                        )
                        return json.dumps({"message": ret})

                    today = datetime.datetime.now().strftime('%Y-%m-%d')
                    current_time = datetime.datetime.now()

                    district_reporters = get_location_role_reporters(
                        db, district_id, config['district_reporters'])
                    subcounty_reporters = get_location_role_reporters(
                        db, subcounty, config['subcounty_reporters'] + ['Subcounty Supervisor'])
                    sms_args = {
                        'village': village,
                        'subcounty': subcounty_name,
                        'district': district,
                        'quantity': qty_nets,
                        'shortcode': config.get('shortcode', '6400')
                    }
                    sched_time = current_time + datetime.timedelta(minutes=SMS_OFFSET_TIME)

                    rx = db.query(
                        "SELECT id FROM village_distribution_log WHERE distribution_log_id =$log_id "
                        "AND village_id = $loc  AND date = $date", {
                            'log_id': log_id, 'loc': reporting_location, 'date': today})
                    if rx:
                        vlog_id = rx[0]["id"]
                        db.query(
                            "UPDATE village_distribution_log SET quantity_received = $qty, "
                            "updated = NOW() "
                            "WHERE id = $id", {'id': vlog_id, 'qty': qty_nets})
                        scheduled_msgs = db.query(
                            "SELECT a.schedule_id, a.level, a.triggered_by FROM distribution_log_schedules a, "
                            " schedules b WHERE a.distribution_log_id = $log_id AND "
                            " b.id = a.schedule_id AND b.status = 'ready' "
                            " AND a.triggered_by = $loc", {'log_id': log_id, 'loc': reporting_location})
                        if scheduled_msgs:
                            for s in scheduled_msgs:
                                db.query(
                                    "SELECT id FROM schedules WHERE id = $sched_id "
                                    "FOR UPDATE NOWAIT", {'sched_id': s['schedule_id']})

                                # build SMS to send to notifying parties
                                sms_text = config['receive_village_nets_sms_template'] % sms_args
                                if s['level'] == 'subcounty':
                                    sms_params = {'text': sms_text, 'to': ' '.join(subcounty_reporters)}
                                    update_queued_sms(db, s['schedule_id'], sms_params, sched_time)

                                elif s['level'] == 'district':
                                    sms_params = {'text': sms_text, 'to': ' '.join(district_reporters)}
                                    update_queued_sms(db, s['schedule_id'], sms_params, sched_time)
                        else:  # no previous schedule that is ready
                            sms_text = config['receive_village_nets_sms_template'] % sms_args
                            sms_params = {'text': sms_text, 'to': ' '.join(district_reporters)}
                            sched_id = queue_schedule(db, sms_params, sched_time)
                            log_schedule(db, log_id, sched_id, 'district', triggered_by=reporting_location)

                            sms_params = {'text': sms_text, 'to': ' '.join(subcounty_reporters)}
                            sched_id = queue_schedule(db, sms_params, sched_time)
                            log_schedule(db, log_id, sched_id, 'subcounty', triggered_by=reporting_location)
                        ret = (
                            "Receipt of %s nets with waybill %s successfully recorded. "
                            "If there's an error please resend" % (qty_nets, waybill)
                        )
                        return json.dumps({"message": ret})
                    else:
                        db.query(
                            "INSERT INTO village_distribution_log(distribution_log_id, village_id, "
                            " quantity_received, date, received_by) VALUES($log_id, $loc, $qty, $date, $received_by) "
                            " RETURNING id ", {
                                'log_id': log_id, 'loc': reporting_location,
                                'qty': qty_nets, 'date': today, 'received_by': reporter_id})
                        ret = (
                            "Receipt of %s nets with waybill %s "
                            "successfully recorded. If there's an error please resend" % (qty_nets, waybill))
                        sms_text = config['receive_village_nets_sms_template'] % sms_args
                        sms_params = {'text': sms_text, 'to': ' '.join(district_reporters)}
                        sched_id = queue_schedule(db, sms_params, sched_time)
                        log_schedule(db, log_id, sched_id, 'district', triggered_by=reporting_location)

                        sms_params = {'text': sms_text, 'to': ' '.join(subcounty_reporters)}
                        sched_id = queue_schedule(db, sms_params, sched_time)
                        log_schedule(db, log_id, sched_id, 'subcounty', triggered_by=reporting_location)
                        return json.dumps({"message": ret})
                else:
                    ret = ("No distribution with delivery note: %s recorded in the system" % waybill)


class DistributeHouseholdNets:
    def POST(self):
        web.header("Content-Type", "application/json; charset=utf-8")
        params = web.input()
        qty_nets = get_webhook_msg(params, 'quantity_nets')
        try:
            qty_nets = int(float(qty_nets))
        except:
            return json.dumps({"message": "The nets received must be a number"})

        phone = params.phone.replace('+', '')
        with db.transaction():
            r = db.query(
                "SELECT id, firstname, reporting_location, district_id, "
                "district, loc_name village "
                "FROM reporters_view4 WHERE replace(telephone, '+', '') = $tel "
                "OR replace(alternate_tel, '+', '') = $tel LIMIT 1", {'tel': phone})
            if r and qty_nets:
                reporter = r[0]
                reporter_id = reporter['id']
                district_id = reporter["district_id"]
                district = reporter["district"]
                reporting_location = reporter['reporting_location']
                village = reporter['village']
                vht = "%s - %s" % (reporter["firstname"], phone)
                res = db.query("SELECT id,name FROM get_ancestors($loc) WHERE type_id=4", {'loc': reporting_location})
                sc = res[0]
                subcounty = sc['id']
                subcounty_name = sc['name']
                res = db.query(
                    "SELECT id, distribution_log_id, village_id, quantity_received, date "
                    "FROM village_distribution_log WHERE village_id = $loc", {
                        'loc': reporting_location})
                if res:
                    log = res[0]
                    vdist_id = log['id']
                    log_id = log['distribution_log_id']  # tying in to original waybill

                    nets_received = log['quantity_received']  # total nets received by village
                    if qty_nets > nets_received:
                        ret = (
                            "You cannot distribute more than you received for your village! "
                            "Please send in the total number distributed today.")
                        return json.dumps({"message": ret})

                    # get what is distributed so far
                    rz = db.query(
                        "SELECT CASE WHEN (sum(quantity) > 0) THEN "
                        " sum(quantity) ELSE 0 END as total FROM household_distribution_log "
                        "WHERE vdist_id = $vdist_id", {
                            'vdist_id': vdist_id})
                    nets_distributed_so_far = rz[0]['total']
                    if (nets_distributed_so_far + qty_nets) > nets_received:
                        ret = (
                            "You cannot distribute more than you received for your village! "
                            "Please send in the total number distributed today. "
                            "Total Received = %s, Total Distributed = %s" % (nets_received, nets_distributed_so_far))
                        return json.dumps({"message": ret})

                    today = datetime.datetime.now().strftime('%Y-%m-%d')
                    current_time = datetime.datetime.now()

                    district_reporters = get_location_role_reporters(
                        db, district_id, config['district_reporters'])
                    subcounty_reporters = get_location_role_reporters(
                        db, subcounty, config['subcounty_reporters'] + ['Subcounty Supervisor'])
                    sms_args = {
                        'village': village,
                        'subcounty': subcounty_name,
                        'district': district,
                        'quantity': qty_nets,
                        'vht': vht,
                        'shortcode': config.get('shortcode', '6400')
                    }
                    sched_time = current_time + datetime.timedelta(minutes=SMS_OFFSET_TIME)
                    rx = db.query(
                        "SELECT id FROM household_distribution_log WHERE vdist_id = $vdist_id "
                        "AND distribution_date = $today AND reporter_id = $reporter_id", {
                            'vdist_id': vdist_id, 'today': today, 'reporter_id': reporter_id})
                    if rx:
                        # lets update today's number
                        hlog_id = rx[0]['id']
                        db.query(
                            "UPDATE household_distribution_log SET quantity=$qty, "
                            "updated=NOW() WHERE id = $id", {'id': hlog_id, 'qty': qty_nets})
                        scheduled_msgs = db.query(
                            "SELECT a.schedule_id, a.level, a.triggered_by FROM distribution_log_schedules a, "
                            " schedules b WHERE a.distribution_log_id = $log_id AND "
                            " b.id = a.schedule_id AND b.status = 'ready' AND a.created > NOW() - '2 hours'::interval"
                            " AND a.triggered_by = $loc", {'log_id': log_id, 'loc': reporting_location})
                        if scheduled_msgs:
                            for s in scheduled_msgs:
                                db.query(
                                    "SELECT id FROM schedules WHERE id = $sched_id "
                                    "FOR UPDATE NOWAIT", {'sched_id': s['schedule_id']})

                                # build SMS to send to notifying parties
                                sms_text = config['household_nets_sms_template'] % sms_args
                                if s['level'] == 'subcounty':
                                    sms_params = {'text': sms_text, 'to': ' '.join(subcounty_reporters)}
                                    update_queued_sms(db, s['schedule_id'], sms_params, sched_time)

                                elif s['level'] == 'district':
                                    sms_params = {'text': sms_text, 'to': ' '.join(district_reporters)}
                                    update_queued_sms(db, s['schedule_id'], sms_params, sched_time)
                        else:  # no previous schedule that is ready
                            sms_text = config['household_nets_sms_template'] % sms_args
                            sms_params = {'text': sms_text, 'to': ' '.join(district_reporters)}
                            sched_id = queue_schedule(db, sms_params, sched_time)
                            log_schedule(db, log_id, sched_id, 'district', triggered_by=reporting_location)

                            sms_params = {'text': sms_text, 'to': ' '.join(subcounty_reporters)}
                            sched_id = queue_schedule(db, sms_params, sched_time)
                            log_schedule(db, log_id, sched_id, 'subcounty', triggered_by=reporting_location)

                        ret = (
                            "You have distributed a total of %(quantity)s nets in %(village)s "
                            "of %(subcounty)s Subcounty today. If there's an error, please resend" % sms_args)
                        return json.dumps({"message": ret})
                    else:
                        db.query(
                            "INSERT INTO household_distribution_log (vdist_id, distribution_date, "
                            "quantity, reporter_id) VALUES($vdist_id, $date, $qty, $reporter_id)", {
                                'vdist_id': vdist_id, 'date': today,
                                'qty': qty_nets, 'reporter_id': reporter_id})
                        ret = (
                            "You have distributed a total of %(quantity)s nets in %(village)s "
                            "of %(subcounty)s Subcounty today. If there's an error, please resend" % sms_args)

                        sms_text = config['household_nets_sms_template'] % sms_args
                        sms_params = {'text': sms_text, 'to': ' '.join(district_reporters)}
                        sched_id = queue_schedule(db, sms_params, sched_time)
                        log_schedule(db, log_id, sched_id, 'district', triggered_by=reporting_location)

                        sms_params = {'text': sms_text, 'to': ' '.join(subcounty_reporters)}
                        sched_id = queue_schedule(db, sms_params, sched_time)
                        log_schedule(db, log_id, sched_id, 'subcounty', triggered_by=reporting_location)
                        return json.dumps({"message": ret})
                else:
                    ret = ("%s village has not yet registered any received nets" % village)
                    return json.dumps({"message": ret})
