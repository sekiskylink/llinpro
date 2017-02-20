import web
from . import csrf_protected, db, require_login, render


class AuditLog:
    @require_login
    def GET(self):
        params = web.input(d_id="")
        logs = db.query(
            "SELECT remote_ip, logtype, actor, action, to_char(created, 'YYYY-MM-DD HH:MI') "
            "as created, detail FROM audit_log ORDER BY id DESC LIMIT 700;")
        l = locals()
        del l['self']
        return render.auditlog(**l)

    @csrf_protected
    @require_login
    def POST(self):
        params = web.input(d_id="")

        with db.transaction():
            pass
        l = locals()
        del l['self']
        return render.auditlog(**l)
