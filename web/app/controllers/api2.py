import json
from . import db
import web
from settings import config
import os
from app.tools.utils import get_basic_auth_credentials, auth_user


class LocationsEndpoint:
    def GET(self, district_code):
        params = web.input(from_date="", type="")
        web.header("Content-Type", "application/json; charset=utf-8")
        username, password = get_basic_auth_credentials()
        r = auth_user(db, username, password)
        if not r[0]:
            web.header('WWW-Authenticate', 'Basic realm="Auth API"')
            web.ctx.status = '401 Unauthorized'
            return json.dumps({'detail': 'Authentication failed!'})

        y = db.query("SELECT id, lft, rght FROM locations WHERE code = $code", {'code': district_code})
        location_id = 0
        if y:
            loc = y[0]
            location_id = loc['id']
            lft = loc['lft']
            rght = loc['rght']
        SQL = (
            "SELECT a.id, a.name, a.code, a.uuid, a.lft, a.rght, a.tree_id, a.tree_parent_id, "
            "b.code as parent_code, c.level, c.name as type, "
            "to_char(a.cdate, 'YYYY-mm-dd') as created "
            " FROM locations a, locations b, locationtype c"
            " WHERE "
            " a.tree_parent_id = b.id "
            " AND a.lft > %s AND a.lft < %s "
            " AND a.type_id = c.id "
        )
        SQL = SQL % (lft, rght)
        if params.from_date:
            SQL += " AND a.cdate >= $date "
        if params.type:
            SQL += " AND c.name = $type "
        r = db.query(SQL, {'id': location_id, 'date': params.from_date, 'type': params.type})
        ret = []
        for i in r:
            ret.append(dict(i))
        return json.dumps(ret)


class LocationsCSVEndpoint:
    def GET(self):
        # params = web.input()
        username, password = get_basic_auth_credentials()
        r = auth_user(db, username, password)
        if not r[0]:
            web.header("Content-Type", "application/json; charset=utf-8")
            web.header('WWW-Authenticate', 'Basic realm="Auth API"')
            web.ctx.status = '401 Unauthorized'
            return json.dumps({'detail': 'Authentication failed!'})
        y = db.query("COPY(SELECT * FROM locations) to '/tmp/llin.csv'  with delimiter ',' csv header;")
        if y:
            static_directory = config.get('static_directory', '/var/www/llinpro/web/static')
            os.popen("zip /tmp/llin.csv.zip /tmp/llin.csv; cp /tmp/llin.csv.zip %s" % static_directory)
            web.header("Content-Type", "application/zip; charset=utf-8")
            # web.header('Content-disposition', 'attachment; filename=%s.csv'%file_name)
            web.seeother("/static/llin.csv.zip")
        else:
            web.header("Content-Type", "application/json; charset=utf-8")
            return json.dumps({'detail': 'CSV download service failed!'})
