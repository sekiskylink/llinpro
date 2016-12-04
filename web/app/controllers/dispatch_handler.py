import web
from . import csrf_protected, db, require_login, render, get_session
from settings import QUANTITY_PER_BALE, config, SMS_OFFSET_TIME
from app.tools.utils import audit_log, get_location_role_reporters, queue_sms, log_schedule, can_still_distribute
import datetime


class Dispatch:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="")
        session = get_session()
        edit_val = params.ed
        warehouses = db.query("SELECT id, name FROM warehouses ORDER BY name")
        districts = db.query(
            "SELECT id, name FROM locations WHERE type_id = "
            "(SELECT id FROM locationtype WHERE name = 'district') ORDER by name")
        if params.ed:
            res = db.query(
                "SELECT * FROM distribution_log WHERE id = $id", {'id': params.ed})
            if res:
                # get values to put in edit form
                r = res[0]
                dres = db.query(
                    "SELECT firstname, telephone FROM reporters "
                    "WHERE id = $id", {'id': r.delivered_by})
                if dres:
                    d = dres[0]
                    driver = d['firstname']
                    driver_tel = d['telephone']
                subcounty = r.destination
                release_order, waybill = (r.release_order, r.waybill)
                quantity_bales, remarks = (r.quantity_bales, r.remarks)
                departure_date, departure_time = (r.departure_date, r.departure_time)
                track_no_plate = r.track_no_plate

        distribution_log = db.query(
            "SELECT * FROM distribution_log_w2sc_view WHERE created_by = $user "
            " ORDER by id DESC",
            {'user': session.sesid})
        l = locals()
        del l['self']
        return render.dispatch(**l)

    @csrf_protected
    @require_login
    def POST(self):
        params = web.input(
            ed="", d_id="", district="", subcounty="", release_order="", waybill="",
            quantity_bales="", warehouse="", warehouse_branch="", departure_date="",
            departure_time="", driver="", driver_tel="", remarks="", track_no_plate="")
        session = get_session()
        current_time = datetime.datetime.now()

        with db.transaction():
            if params.ed:
                q = db.query("SELECT id FROM reporters WHERE telephone = $tel", {'tel': params.driver_tel})
                if q:
                    driver_id = q[0]['id']
                else:
                    q = db.query(
                        "INSERT INTO reporters (firstname, telephone) "
                        " VALUES ($name, $tel) RETURNING id",
                        {'name': params.driver, 'tel': params.driver_tel})
                    driver_id = q[0]['id']
                    db.query(
                        "INSERT INTO reporter_groups_reporters (group_id, reporter_id) "
                        "VALUES ((SELECT id FROM reporter_groups WHERE name = 'Driver'), $reporter_id)",
                        {'reporter_id', driver_id})
                r = db.query(
                    "UPDATE distribution_log SET release_order=$release_order, "
                    "destination=$destination, waybill=$waybill, warehouse_branch = $branch, "
                    "departure_date=$ddate, departure_time=$dtime, remarks=$remarks, "
                    "delivered_by=$delivered_by WHERE id = $id RETURNING id", {
                        'release_order': params.release_order,
                        'destination': params.subcounty, 'waybill': params.waybill,
                        'branch': params.warehouse_branch, 'ddate': params.departure_date,
                        'dtime': params.departure_time, 'remarks': params.remarks,
                        'delivered_by': driver_id,
                        'id': params.ed
                    })
                if r:
                    data_id = r[0]['id']
                    log_dict = {
                        'logtype': 'Distribution', 'action': 'Update', 'actor': session.username,
                        'ip': web.ctx['ip'],
                        'descr': 'Updated distribution data id:%s, Waybill:%s, Qty (bales):%s' % (
                            data_id, params.waybill, params.quantity),
                        'user': session.sesid
                    }
                    audit_log(db, log_dict)
                return web.seeother("/dispatch")
            else:
                # check whether what we want to distribute is available in stock
                if not can_still_distribute:
                    session.ddata_err = ("You cannot distribute more than is available for distribution!")
                    return web.seeother("/dispatch")

                has_entry = db.query(
                    "SELECT id FROM distribution_log WHERE waybill=$waybill",
                    {'waybill': params.waybill})
                if has_entry:
                    session.ddata_err = ("Entry with Waybill: %s already entered!" % params.waybill)
                    return web.seeother("/dispatch")
                session.ddata_err = ""
                q = db.query("SELECT id FROM reporters WHERE telephone = $tel", {'tel': params.driver_tel})
                if q:
                    driver_id = q[0]['id']
                else:
                    q = db.query(
                        "INSERT INTO reporters (firstname, telephone) "
                        " VALUES ($name, $tel) RETURNING id",
                        {'name': params.driver, 'tel': params.driver_tel})
                    driver_id = q[0]['id']
                    db.query(
                        "INSERT INTO reporter_groups_reporters (group_id, reporter_id) "
                        "VALUES ((SELECT id FROM reporter_groups WHERE name = 'Driver'), $reporter_id)",
                        {'reporter_id': driver_id})

                r = db.query(
                    "INSERT INTO distribution_log (source, dest, release_order, waybill, "
                    " quantity_bales, quantity_nets, remarks, warehouse_branch, "
                    " departure_date, departure_time, destination, delivered_by, created_by, track_no_plate) "
                    "VALUES('national', 'subcounty', $release_order, $waybill, $quantity_bales, "
                    "$quantity_nets, $remarks, $branch, $ddate, $dtime, $destination, "
                    "$delivered_by, $user, $noplate) "
                    "RETURNING id",
                    {
                        'release_order': params.release_order, 'waybill': params.waybill,
                        'quantity_bales': params.quantity_bales,
                        'quantity_nets': (QUANTITY_PER_BALE * int(params.quantity_bales)),
                        'remarks': params.remarks, 'branch': params.warehouse_branch,
                        'ddate': params.departure_date,
                        'dtime': params.departure_time,
                        'destination': params.subcounty,
                        'delivered_by': driver_id,
                        'user': session.sesid,
                        'noplate': params.track_no_plate
                    })
                if r:
                    log_id = r[0]['id']

                    # sched_time allows to give distribution_log edits sometime #SMS_OFFSET_TIME
                    sched_time = current_time + datetime.timedelta(minutes=SMS_OFFSET_TIME)

                    district_reporters = get_location_role_reporters(db, params.district, config['district_reporters'])
                    sms_params = {'text': 'test district SMS', 'to': ','.join(district_reporters)}
                    sched_id = queue_sms(db, sms_params, sched_time, session.sesid)
                    log_schedule(db, log_id, sched_id, 'district')
                    # print "+=======+=======+===>", district_reporters

                    national_reporters = get_location_role_reporters(db, 1, config['national_reporters'])
                    sms_params = {'text': 'test national SMS', 'to': ','.join(national_reporters)}
                    sched_id = queue_sms(db, sms_params, sched_time, session.sesid)
                    log_schedule(db, log_id, sched_id, 'national')
                    # print "*=======*=======*===>", national_reporters

                    subcounty_reporters = get_location_role_reporters(db, params.subcounty, config['subcounty_reporters'])
                    sms_params = {'text': 'test subcounty SMS', 'to': ','.join(subcounty_reporters)}
                    sched_id = queue_sms(db, sms_params, sched_time, session.sesid)
                    log_schedule(db, log_id, sched_id, 'subcounty')
                    # print "@=======@=======@===>", subcounty_reporters

                    log_dict = {
                        'logtype': 'Distribution', 'action': 'Create', 'actor': session.username,
                        'ip': web.ctx['ip'],
                        'descr': 'Added distribution entry id:%s, Waybill:%s, Qty (bales):%s' % (
                            log_id, params.waybill, params.quantity_bales),
                        'user': session.sesid
                    }
                    audit_log(db, log_dict)

                return web.seeother("/dispatch")

        l = locals()
        del l['self']
        return render.dispatch(**l)
