import json
from . import db
import web
from settings import config, SMS_OFFSET_TIME
from app.tools.utils import get_location_role_reporters, update_queued_sms
import datetime


class FixReceiveVillageNets:
    def POST(self):
        web.header("Content-Type", "application/json; charset=utf-8")
        params = web.input(waybill="", nets="", phone="", date="")
        waybill = params.waybill
        qty_nets = params.nets
        date = params.date
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
                                    # update_queued_sms(db, s['schedule_id'], sms_params, sched_time)

                                elif s['level'] == 'district':
                                    sms_params = {'text': sms_text, 'to': ' '.join(district_reporters)}
                                    # update_queued_sms(db, s['schedule_id'], sms_params, sched_time)
                        else:  # no previous schedule that is ready
                            sms_text = config['receive_village_nets_sms_template'] % sms_args
                            sms_params = {'text': sms_text, 'to': ' '.join(district_reporters)}
                            # sched_id = queue_schedule(db, sms_params, sched_time)
                            # log_schedule(db, log_id, sched_id, 'district', triggered_by=reporting_location)

                            sms_params = {'text': sms_text, 'to': ' '.join(subcounty_reporters)}
                            # sched_id = queue_schedule(db, sms_params, sched_time)
                            # log_schedule(db, log_id, sched_id, 'subcounty', triggered_by=reporting_location)
                        ret = (
                            "Receipt of %s nets with waybill %s successfully recorded. "
                            "If there's an error please resend" % (qty_nets, waybill)
                        )
                        return json.dumps({"message": ret})
                    else:
                        db.query(
                            "INSERT INTO village_distribution_log(distribution_log_id, village_id, "
                            " quantity_received, date, received_by, created) "
                            "VALUES($log_id, $loc, $qty, $date, $received_by, $created) "
                            " RETURNING id ", {
                                'log_id': log_id, 'loc': reporting_location,
                                'qty': qty_nets, 'date': today, 'received_by': reporter_id,
                                'created': date})
                        ret = (
                            "Receipt of %s nets with waybill %s "
                            "successfully recorded. If there's an error please resend" % (qty_nets, waybill))
                        sms_text = config['receive_village_nets_sms_template'] % sms_args
                        sms_params = {'text': sms_text, 'to': ' '.join(district_reporters)}
                        # sched_id = queue_schedule(db, sms_params, sched_time)
                        # log_schedule(db, log_id, sched_id, 'district', triggered_by=reporting_location)

                        sms_params = {'text': sms_text, 'to': ' '.join(subcounty_reporters)}
                        # sched_id = queue_schedule(db, sms_params, sched_time)
                        # log_schedule(db, log_id, sched_id, 'subcounty', triggered_by=reporting_location)
                        return json.dumps({"message": ret})
                else:
                    ret = ("No distribution with delivery note: %s recorded in the system" % waybill)


class FixDistributeHouseholdNets:
    def POST(self):
        web.header("Content-Type", "application/json; charset=utf-8")
        params = web.input(net="", phone="")
        qty_nets = params.nets
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
                                    # update_queued_sms(db, s['schedule_id'], sms_params, sched_time)
                        else:  # no previous schedule that is ready
                            sms_text = config['household_nets_sms_template'] % sms_args
                            sms_params = {'text': sms_text, 'to': ' '.join(district_reporters)}
                            # sched_id = queue_schedule(db, sms_params, sched_time)
                            # log_schedule(db, log_id, sched_id, 'district', triggered_by=reporting_location)

                            sms_params = {'text': sms_text, 'to': ' '.join(subcounty_reporters)}
                            # sched_id = queue_schedule(db, sms_params, sched_time)
                            # log_schedule(db, log_id, sched_id, 'subcounty', triggered_by=reporting_location)

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
                        # sched_id = queue_schedule(db, sms_params, sched_time)
                        # log_schedule(db, log_id, sched_id, 'district', triggered_by=reporting_location)

                        sms_params = {'text': sms_text, 'to': ' '.join(subcounty_reporters)}
                        # sched_id = queue_schedule(db, sms_params, sched_time)
                        # log_schedule(db, log_id, sched_id, 'subcounty', triggered_by=reporting_location)
                        return json.dumps({"message": ret})
                else:
                    ret = ("%s village has not yet registered any received nets" % village)
                    return json.dumps({"message": ret})
