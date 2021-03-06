from settings import config
import requests
import json
import web
import re
import base64
import phonenumbers
import simplejson
import psycopg2.extras


def format_msisdn(msisdn=None):
    """ given a msisdn, return in E164 format """
    assert msisdn is not None
    msisdn = msisdn.replace(' ', '')
    num = phonenumbers.parse(msisdn, getattr(config, 'country', 'UG'))
    is_valid = phonenumbers.is_valid_number(num)
    if not is_valid:
        return None
    return phonenumbers.format_number(
        num, phonenumbers.PhoneNumberFormat.E164)


def lit(**keywords):
    return keywords


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


def default(*args):
    p = [i for i in args if i or i == 0]
    if p.__len__():
        return p[0]
    if args.__len__():
        return args[args.__len__() - 1]
    return None


def post_request(data, url=config['default_api_uri']):
    response = requests.post(url, data=data, headers={
        'Content-type': 'application/json',
        'Authorization': 'Token %s' % config['api_token']})
    return response


def auth_user(db, username, password):
    sql = (
        "SELECT a.id, a.firstname, a.lastname, b.name as role, a.user_role "
        "FROM users a, user_roles b "
        "WHERE username = $username AND password = crypt($passwd, password) "
        "AND a.user_role = b.id AND is_active = 't'")
    res = db.query(sql, {'username': username, 'passwd': password})
    if not res:
        return False, "Wrong username or password"
    else:
        return True, res[0]


def role_permissions(db, role):
    sql = ("SELECT sys_module, sys_perms FROM user_role_permissions WHERE user_role = $role")
    ret = {}
    res = db.query(sql, {'role': role})
    for r in res:
        ret[r['sys_module']] = r['sys_perms']
    return ret


def has_perm(perms_dict, module, perm):
    if module in perms_dict:
        return perms_dict[module].__contains__(perm)
    return False


def audit_log(db, log_dict={}):
    sql = (
        "INSERT INTO audit_log (logtype, actor, action, remote_ip, detail, created_by) "
        " VALUES ($logtype, $actor, $action, $ip, $descr, $user) "
    )
    db.query(sql, log_dict)
    return None


def get_basic_auth_credentials():
    auth = web.ctx.env.get('HTTP_AUTHORIZATION')
    if not auth:
        return (None, None)
    auth = re.sub('^Basic ', '', auth)
    username, password = base64.decodestring(auth).split(':')
    return username, password


def get_location_role_reporters(db, location_id, roles=[], include_alt=True):
    """Returns a contacts list of reporters of specified roles attached to a location
    include_alt allows to add alternate telephone numbers to returned list
    """
    SQL = (
        "SELECT telephone, alternate_tel FROM reporters_view2 WHERE "
        "role IN (%s) " % ','.join(["'%s'" % i for i in roles]))
    SQL += " AND reporting_location = $location"
    res = db.query(SQL, {'location': location_id})
    ret = []
    if res:
        for r in res:
            telephone = r['telephone']
            alternate_tel = r['alternate_tel']
            if telephone:
                ret.append(format_msisdn(telephone))
            if alternate_tel and include_alt:
                ret.append(format_msisdn(alternate_tel))
    return list(set(ret))


def queue_schedule(db, params, run_time, user=None, stype='sms'):  # params has the text, recipients and other params
    res = db.query(
        "INSERT INTO schedules (params, run_time, type, created_by) "
        " VALUES($params, $runtime, $type, $user) RETURNING id",
        {
            'params': psycopg2.extras.Json(params, dumps=simplejson.dumps),
            'runtime': run_time,
            'user': user,
            'type': stype
        })
    if res:
        return res[0]['id']
    return None


def update_queued_sms(db, sched_id, params, run_time, user=None):
    db.query(
        "UPDATE schedules SET params=$params, run_time=$runtime, updated_by=$user, "
        " status='ready', updated=now() WHERE id=$id",
        {
            'params': psycopg2.extras.Json(params, dumps=simplejson.dumps),
            'runtime': run_time,
            'user': user,
            'id': sched_id
        })


def log_schedule(db, distribution_log_id, sched_id, level, triggered_by=1):
    db.query(
        "INSERT INTO distribution_log_schedules(distribution_log_id, schedule_id, level, triggered_by) "
        "VALUES($log_id, $sched_id, $level, $triggered_by)", {
            'log_id': distribution_log_id, 'sched_id': sched_id,
            'level': level, 'triggered_by': triggered_by})


def can_still_distribute(db, amount, reverse_amount=0):
    """Checks whether we can actually distribute nets based on stock
    reverse_amount helps when one is editing a distribution, so it is equal to qty of bales
    before edit
    """
    res = db.query(
        "SELECT CASE WHEN SUM(quantity_bales) > 0 THEN SUM(quantity_bales) "
        "ELSE 0 END AS total FROM national_delivery_log")

    if res and len(res) > 0:
        total_nets = res[0]['total']
        SQL = (
            "SELECT CASE WHEN SUM(quantity_bales) > 0 THEN SUM(quantity_bales) "
            "ELSE 0 END AS total FROM distribution_log_w2sc_view;")
        r = db.query(SQL)
        if r:
            sc_dist = r[0]['total']
            if reverse_amount:
                currently_distributed = sc_dist - reverse_amount
                available = total_nets - currently_distributed
                # print "****TOTAL:%s====AVAIL:%s======AMOUNT:%s" % (total_nets, available, amount)
                return available >= amount
            available = total_nets - sc_dist
            # print "####TOTAL:%s====AVAIL:%s======AMOUNT:%s" % (total_nets, available, amount)
            return available >= amount
    return False
