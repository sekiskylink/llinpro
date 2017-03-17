# -*- coding: utf-8 -*-

"""This module contains the main handler of the application.
"""

import web
from . import render
from . import csrf_protected, db, get_session, put_session
from app.tools.utils import auth_user, audit_log, role_permissions, has_perm


class Index:
    def GET(self):
        l = locals()
        del l['self']
        return render.login(**l)

    @csrf_protected
    def POST(self):
        session = get_session()
        params = web.input(username="", password="")
        username = params.username
        password = params.password
        r = auth_user(db, username, password)
        if r[0]:
            session.loggedin = True
            info = r[1]
            session.name = info.firstname + " " + info.lastname
            session.username = username
            session.sesid = info.id
            session.role = info.role
            session.perms = role_permissions(db, info.user_role)
            # get system permissions at log in time
            session.can_view_reports = has_perm(session.perms, 'Reports', 'r')
            session.can_view_warehouse = has_perm(session.perms, 'Warehouse', 'r')
            session.can_manage_warehouse = has_perm(session.perms, 'Warehouse', 'w')
            session.can_view_reporters = has_perm(session.perms, 'Reporters', 'r')
            session.can_manage_reporters = has_perm(session.perms, 'Reporters', 'w')
            session.can_view_dpoints = has_perm(session.perms, 'Distribution Points', 'r')
            session.can_manage_dpoints = has_perm(session.perms, 'Distribution Points', 'w')
            session.can_view_adminunits = has_perm(session.perms, 'Admin Units', 'r')
            session.can_manage_adminunits = has_perm(session.perms, 'Admin Units', 'w')
            put_session(session)
            log_dict = {
                'logtype': 'Web', 'action': 'Login', 'actor': username,
                'ip': web.ctx['ip'], 'descr': 'User %s logged in' % username,
                'user': info.id
            }
            audit_log(db, log_dict)

            l = locals()
            del l['self']
            if info.role == 'Warehouse Manager':
                return web.seeother("/warehousedata")
            elif info.role == 'Micro Planning':
                return web.seeother("/reporters")
            elif info.role == 'Data Manager':
                return web.seeother("/adminunits")
            else:
                return web.seeother("/dashboard")
        else:
            session.loggedin = False
            session.logon_err = r[1]
        l = locals()
        del l['self']
        return render.login(**l)


class Logout:
    def GET(self):
        session = get_session()
        log_dict = {
            'logtype': 'Web', 'action': 'Logout', 'actor': session.username,
            'ip': web.ctx['ip'], 'descr': 'User %s logged out' % session.username,
            'user': session.sesid
        }
        audit_log(db, log_dict)
        session.kill()
        return web.seeother("/")
