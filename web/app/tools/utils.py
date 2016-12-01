from settings import config
import requests
import web
import re
import base64
import phonenumbers


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
        "SELECT a.id, a.firstname, a.lastname, b.name as role "
        "FROM users a, user_roles b "
        "WHERE username = $username AND password = crypt($passwd, password) "
        "AND a.user_role = b.id AND is_active = 't'")
    res = db.query(sql, {'username': username, 'passwd': password})
    if not res:
        return False, "Wrong username or password"
    else:
        return True, res[0]


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
