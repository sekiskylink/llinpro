import os
import web
import json
from . import csrf_protected, db, require_login, render
from settings import config

script_dir = os.path.split(os.path.abspath(__file__))[0]
parent_dir = os.path.abspath(os.path.join(script_dir, '..'))


class SMSLog:
    @require_login
    def GET(self):
        params = web.input(d_id="")
        res = db.query(
            "SELECT * FROM sms_stats ORDER by id desc  ")
        l = locals()
        del l['self']
        return render.smslog(**l)

    @csrf_protected
    @require_login
    def POST(self):
        params = web.input(d_id="")

        with db.transaction():
            pass
        l = locals()
        del l['self']
        return render.smslog(**l)


class KannelSeries:
    def GET(self):
        params = web.input(id="")
        if params.id:
            rs = db.query(
                "SELECT * FROM sms_stats WHERE id = $id", {'id': params.id})
            ret = ""
            if rs:
                r = rs[0]
                # period = "For %s (Last updated: %s)" % (r['month'], r['updated'])
                incoming = "Incoming,%s,%s,%s,%s" % (r['mtn_in'], r['airtel_in'], r['africel_in'], r['utl_in'])
                outgoing = "Outgoing,%s,%s,%s,%s" % (r['mtn_out'], r['airtel_out'], r['africel_out'], r['utl_out'])
                # ret = period + "\n" + incoming + "\n" + outgoing
                ret = incoming + "\n" + outgoing
            return ret
        return ""


class Refresh:
    def GET(self):
        params = web.input(month="")
        web.header('Content-Type', 'application/json')
        if params.month:
            print params.month
            script_path = script_dir + os.sep + "parse_kannel_log.py"
            cmd = "%s %s -v -m %s" % (config['python_script'], script_path, params.month)
            print cmd
            r = os.popen(cmd)
        return json.dumps(r.read().strip())
