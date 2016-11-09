import web
from . import csrf_protected, db, get_session, require_login, render


class Users:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="")
        edit_val = params.ed
        session = get_session()

        if params.ed:
            r = db.query(
                "SELECT a.id, a.firstname, a.lastname, a.username, a.email, a.telephone, "
                "a.is_active, b.id as role "
                "FROM users a, user_roles b "
                "WHERE a.id = $id AND a.user_role = b.id", {'id': params.ed})
            if r and (session.role == 'Administrator' or '%s' % session.sesid == edit_val):
                u = r[0]
                firstname = u.firstname
                lastname = u.lastname
                telephone = u.telephone
                email = u.email
                username = u.username
                role = u.role
                is_active = u.is_active
                is_super = True if u.role == 'Administrator' else False

        if params.d_id:
            if session.role == 'Administrator':
                db.query("DELETE FROM users WHERE id=$id", {'id': params.d_id})

        roles = db.query("SELECT id, name FROM user_roles ORDER by name")
        if session.role == 'Administrator':
            users = db.query(
                "SELECT a.id, a.firstname, a.lastname, a.username, a.email, a.telephone, b.name as role "
                "FROM users a, user_roles b WHERE a.user_role = b.id")
        else:
            users = db.query(
                "SELECT a.id, a.firstname, a.lastname, a.username, a.email, a.telephone, b.name as role "
                "FROM users a, user_roles b WHERE a.user_role = b.id "
                "AND a.id=$id", {'id': session.sesid})
        l = locals()
        del l['self']
        return render.users(**l)

    @csrf_protected
    def POST(self):
        params = web.input(
            firstname="", lastname="", telephone="", username="", email="", passwd="",
            cpasswd="", is_active="", is_super="", page="1", ed="", d_id="")
        try:
            page = int(params.page)
        except:
            page = 1
        is_active = 't' if params.is_active == "on" else 'f'
        role = 'Administrator' if params.is_super == "on" else 'Basic'
        with db.transaction():
            if params.ed:
                db.query(
                    "UPDATE users SET firstname=$firstname, lastname=$lastname, "
                    "telephone=$telephone, email=$email, username=$username, "
                    "password = crypt($cpasswd, gen_salt('bf')), "
                    "is_active=$is_active, "
                    "user_role=(SELECT id FROM user_roles WHERE name=$role) "
                    "WHERE id = $id", {
                        'firstname': params.firstname, 'lastname': params.lastname,
                        'telephone': params.telephone, 'email': params.email,
                        'username': params.username, 'cpasswd': params.cpasswd,
                        'role': role, 'is_active': is_active, 'id': params.ed
                    }
                )
                return web.seeother("/users")
            else:
                db.query(
                    "INSERT INTO users (firstname, lastname, telephone, email, "
                    "username, password, is_active, user_role) "
                    "VALUES($firstname, $lastname, $telephone, $email, $username, "
                    "crypt($cpasswd, gen_salt('bf')), $is_active, "
                    "(SELECT id FROM user_roles WHERE name=$role))", {
                        'firstname': params.firstname, 'lastname': params.lastname,
                        'telephone': params.telephone, 'email': params.email,
                        'username': params.username, 'cpasswd': params.cpasswd,
                        'role': role, 'is_active': is_active, 'id': params.ed
                    }
                )
                return web.seeother("/users")
        l = locals()
        del l['self']
        return render.users(**l)
