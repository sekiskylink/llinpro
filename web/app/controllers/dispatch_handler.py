import web
from . import csrf_protected, db, require_login, render, get_session
from settings import QUANTITY_PER_BALE, config, SMS_OFFSET_TIME
from app.tools.utils import audit_log, get_location_role_reporters, queue_schedule, log_schedule
from app.tools.utils import can_still_distribute, update_queued_sms
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
        district = {}
        allow_edit = False
        try:
            edit_val = int(params.ed)
            allow_edit = True
        except ValueError:
            pass

        if params.ed and allow_edit:
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
                warehouse_branch = r.warehouse_branch
                departure_date, departure_time = (r.departure_date, r.departure_time)
                track_no_plate = r.track_no_plate
                district = ""
                subcounties = []
                ancestors = db.query(
                    "SELECT id, name, level FROM get_ancestors($loc) "
                    "WHERE level = 2 ORDER BY level DESC;", {'loc': r.destination})
                if ancestors:
                    district = ancestors[0]
                    subcounties = db.query("SELECT id, name FROM get_children($id)", {'id': district['id']})
                wx = db.query(
                    "SELECT id FROM warehouses WHERE id = "
                    "(SELECT warehouse_id FROM warehouse_branches "
                    " WHERE id = $branch) ", {'branch': warehouse_branch})
                warehouse = wx[0]['id']
                if warehouse:
                    branches = db.query(
                        "SELECT id, name FROM warehouse_branches WHERE warehouse_id = "
                        "$wid", {'wid': warehouse})

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
            departure_time="", driver="", driver_tel="", remarks="", track_no_plate="",
            quantity_bales_old=0)
        session = get_session()
        current_time = datetime.datetime.now()
        allow_edit = False
        try:
            edit_val = int(params.ed)
            allow_edit = True
        except ValueError:
            pass

        with db.transaction():
            if params.ed and allow_edit:
                q = db.query("SELECT id FROM reporters WHERE telephone = $tel", {'tel': params.driver_tel})
                if q:
                    driver_id = q[0]['id']
                else:
                    q = db.query(
                        "INSERT INTO reporters (firstname, telephone, reporting_location) "
                        " VALUES ($name, $tel, 1) RETURNING id",
                        {'name': params.driver, 'tel': params.driver_tel})
                    driver_id = q[0]['id']
                    db.query(
                        "INSERT INTO reporter_groups_reporters (group_id, reporter_id) "
                        "VALUES ((SELECT id FROM reporter_groups WHERE name = 'Driver'), $reporter_id)",
                        {'reporter_id': driver_id})

                    # Schedule a push_contact to Push driver to RapidPro
                    contact_params = {
                        'phone': params.driver_tel,
                        'name': params.driver,
                        'groups': ['Driver']
                    }

                    sync_time = current_time + datetime.timedelta(seconds=5)  # XXX consider making the seconds configurable
                    queue_schedule(db, contact_params, sync_time, session.sesid, 'push_contact')

                # check if new quantities leave us in a consistent state
                old_quantity = int(params.quantity_bales_old)
                quantity_bales = int(params.quantity_bales)
                if not can_still_distribute(db, quantity_bales, old_quantity):
                    session.ddata_err = ("You cannot distribute more than is available for distribution!")
                    return web.seeother("/dispatch")
                session.ddata_err = ""
                r = db.query(
                    "UPDATE distribution_log SET release_order=$release_order, "
                    "destination=$destination, waybill=$waybill, warehouse_branch = $branch, "
                    "departure_date=$ddate, departure_time=$dtime, remarks=$remarks, "
                    "quantity_bales=$quantity_bales, quantity_nets=$quantity_nets, "
                    "delivered_by=$delivered_by WHERE id = $id RETURNING id", {
                        'release_order': params.release_order,
                        'destination': params.subcounty, 'waybill': params.waybill,
                        'branch': params.warehouse_branch, 'ddate': params.departure_date,
                        'dtime': params.departure_time, 'remarks': params.remarks,
                        'quantity_bales': params.quantity_bales,
                        'quantity_nets': (QUANTITY_PER_BALE * int(params.quantity_bales)),
                        'delivered_by': driver_id,
                        'id': params.ed
                    })

                if r:
                    data_id = r[0]['id']
                    subcounty = ""
                    district = ""
                    # get subcounty name to use in SMS
                    sc = db.query(
                        "SELECT get_location_name($subcounty) as name;",
                        {'subcounty': params.subcounty})
                    if sc:
                        subcounty = sc[0]['name']

                    # get district name to use in SMS
                    dist = db.query(
                        "SELECT get_district($subcounty) as name;",
                        {'subcounty': params.subcounty})
                    if dist:
                        district = dist[0]['name']

                    # sched_time = time to send SMS
                    sched_time = current_time + datetime.timedelta(minutes=SMS_OFFSET_TIME)

                    # appropriately edit scheduled messages
                    sms_args = {
                        'subcounty': subcounty,
                        'district': district,
                        'waybill': params.waybill,
                        'quantity': quantity_bales,
                        'shortcode': config.get('shortcode', '6400')
                    }
                    national_reporters = get_location_role_reporters(
                        db, 1, config['national_reporters'])
                    district_reporters = get_location_role_reporters(
                        db, params.district, config['district_reporters'])
                    subcounty_reporters = get_location_role_reporters(
                        db, params.subcounty, config['subcounty_reporters'])

                    scheduled_msgs = db.query(
                        "SELECT a.schedule_id, a.level FROM distribution_log_schedules a, "
                        " schedules b WHERE a.distribution_log_id = $log_id AND "
                        " b.id = a.schedule_id AND b.status = 'ready'", {'log_id': data_id})  # XXX 'ready'
                    if scheduled_msgs:  # we still have ready schedules
                        for s in scheduled_msgs:
                            sched = db.query(
                                "SELECT id FROM schedules WHERE id = $sched_id "
                                "FOR UPDATE NOWAIT", {'sched_id': s['schedule_id']})

                            # build SMS to send to notifying parties
                            sms_text = config['national_sms_template'] % sms_args
                            if s['level'] == 'national':
                                sms_params = {'text': sms_text, 'to': ','.join(national_reporters)}
                                update_queued_sms(db, s['schedule_id'], sms_params, sched_time, session.sesid)

                            elif s['level'] == 'district':
                                sms_params = {'text': sms_text, 'to': ','.join(district_reporters)}
                                update_queued_sms(db, s['schedule_id'], sms_params, sched_time, session.sesid)

                            elif s['level'] == 'subcounty':
                                sms_text += (
                                    '\n Once received / offloaded, please send '
                                    '"REC %(waybill)s %(quantity)s" to %(shortcode)s' % sms_args)
                                sms_params = {'text': sms_text, 'to': ','.join(subcounty_reporters)}
                                update_queued_sms(db, s['schedule_id'], sms_params, sched_time, session.sesid)

                            elif s['level'] == 'driver':
                                driver_sms_text = config['driver_sms_template'] % sms_args
                                sms_params = {'text': driver_sms_text, 'to': params.driver_tel}
                                update_queued_sms(db, s['schedule_id'], sms_params, sched_time, session.sesid)
                    else:  # no ready schedules were found
                        sms_text = config['national_sms_template'] % sms_args
                        sms_params = {'text': sms_text, 'to': ','.join(district_reporters)}
                        sched_id = queue_schedule(db, sms_params, sched_time, session.sesid)
                        log_schedule(db, data_id, sched_id, 'district')
                        # print "+=======+=======+===>", district_reporters

                        sms_params = {'text': sms_text, 'to': ','.join(national_reporters)}
                        sched_id = queue_schedule(db, sms_params, sched_time, session.sesid)
                        log_schedule(db, data_id, sched_id, 'national')
                        # print "*=======*=======*===>", national_reporters

                        sms_text += (
                            '\n Once received / offloaded, please send '
                            '"REC %(waybill)s %(quantity)s" to %(shortcode)s' % sms_args)
                        sms_params = {'text': sms_text, 'to': ','.join(subcounty_reporters)}
                        sched_id = queue_schedule(db, sms_params, sched_time, session.sesid)
                        log_schedule(db, data_id, sched_id, 'subcounty')
                        # print "@=======@=======@===>", subcounty_reporters

                        # for the driver
                        driver_sms_text = config['driver_sms_template'] % sms_args
                        sms_params = {'text': driver_sms_text, 'to': params.driver_tel}
                        sched_id = queue_schedule(db, sms_params, sched_time, session.sesid)
                        log_schedule(db, data_id, sched_id, 'driver')

                    log_dict = {
                        'logtype': 'Distribution', 'action': 'Update', 'actor': session.username,
                        'ip': web.ctx['ip'],
                        'descr': 'Updated distribution data id:%s, Waybill:%s, Qty (bales):%s' % (
                            data_id, params.waybill, params.quantity_bales),
                        'user': session.sesid
                    }
                    audit_log(db, log_dict)
                return web.seeother("/dispatch")
            else:
                # check whether what we want to distribute is available in stock
                quantity_bales = int(params.quantity_bales)
                if not can_still_distribute(db, quantity_bales):
                    session.ddata_err = ("You cannot distribute more than is available for distribution!")
                    return web.seeother("/dispatch")
                session.ddata_err = ""

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
                        "INSERT INTO reporters (firstname, telephone, reporting_location) "
                        " VALUES ($name, $tel, 1) RETURNING id",
                        {'name': params.driver, 'tel': params.driver_tel})
                    driver_id = q[0]['id']
                    db.query(
                        "INSERT INTO reporter_groups_reporters (group_id, reporter_id) "
                        "VALUES ((SELECT id FROM reporter_groups WHERE name = 'Driver'), $reporter_id)",
                        {'reporter_id': driver_id})
                    # Schedule a push_contact to Push driver to RapidPro
                    contact_params = {
                        'phone': params.driver_tel,
                        'name': params.driver,
                        'groups': ['Driver'],
                    }

                    sync_time = current_time + datetime.timedelta(seconds=5)  # XXX consider making the seconds configurable
                    queue_schedule(db, contact_params, sync_time, session.sesid, 'push_contact')

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
                    subcounty = ""
                    district = ""
                    # get subcounty name to use in SMS
                    sc = db.query(
                        "SELECT get_location_name($subcounty) as name;",
                        {'subcounty': params.subcounty})
                    if sc:
                        subcounty = sc[0]['name']

                    # get district name to use in SMS
                    dist = db.query(
                        "SELECT get_district($subcounty) as name;",
                        {'subcounty': params.subcounty})
                    if dist:
                        district = dist[0]['name']

                    # sched_time allows to give distribution_log edits sometime #SMS_OFFSET_TIME
                    sched_time = current_time + datetime.timedelta(minutes=SMS_OFFSET_TIME)

                    # build SMS to send to notifying parties
                    sms_args = {
                        'subcounty': subcounty,
                        'district': district,
                        'waybill': params.waybill,
                        'quantity': quantity_bales,
                        'shortcode': config.get('shortcode', '6400')
                    }
                    sms_text = config['national_sms_template'] % sms_args

                    district_reporters = get_location_role_reporters(db, params.district, config['district_reporters'])
                    sms_params = {'text': sms_text, 'to': ','.join(district_reporters)}
                    sched_id = queue_schedule(db, sms_params, sched_time, session.sesid)
                    log_schedule(db, log_id, sched_id, 'district')
                    # print "+=======+=======+===>", district_reporters

                    national_reporters = get_location_role_reporters(db, 1, config['national_reporters'])
                    sms_params = {'text': sms_text, 'to': ','.join(national_reporters)}
                    sched_id = queue_schedule(db, sms_params, sched_time, session.sesid)
                    log_schedule(db, log_id, sched_id, 'national')
                    # print "*=======*=======*===>", national_reporters

                    subcounty_reporters = get_location_role_reporters(db, params.subcounty, config['subcounty_reporters'])
                    sms_text += (
                        '\n Once received / offloaded, please send '
                        '"REC %(waybill)s %(quantity)s" to %(shortcode)s' % sms_args)
                    sms_params = {'text': sms_text, 'to': ','.join(subcounty_reporters)}
                    sched_id = queue_schedule(db, sms_params, sched_time, session.sesid)
                    log_schedule(db, log_id, sched_id, 'subcounty')
                    # print "@=======@=======@===>", subcounty_reporters

                    # for the driver
                    driver_sms_text = config['driver_sms_template'] % sms_args
                    sms_params = {'text': driver_sms_text, 'to': params.driver_tel}
                    sched_id = queue_schedule(db, sms_params, sched_time, session.sesid)
                    log_schedule(db, log_id, sched_id, 'driver')

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
