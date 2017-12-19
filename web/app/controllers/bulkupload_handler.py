import web
import os
import tempfile
from . import require_login, render, get_session
from settings import BASE_DIR
UPLOAD_SCRIPT = BASE_DIR + "/load_warehouse_data.py"


class BulkUpload:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="")
        edit_val = params.ed
        session = get_session()

        l = locals()
        del l['self']
        return render.bulkupload(**l)

    @require_login
    def POST(self):
        params = web.input(uploadfile={})
        session = get_session()

        if session.role == 'District User':
            district = session.username.capitalize()
            user = session.username
            if params.uploadfile.type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                # print dir(params.uploadfile)
                f = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
                # print f.name
                f.write(params.uploadfile.file.read())
                cmd = UPLOAD_SCRIPT + " -f %s -u %s" % (f.name, user)
                try:
                    f.close()
                except:
                    pass
                # print cmd
                os.popen(cmd)
                os.unlink(f.name)
            else:
                sess_err = "Upload file should be an Excel spreadsheet."

        l = locals()
        del l['self']
        return render.bulkupload(**l)
