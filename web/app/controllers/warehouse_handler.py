# -*- coding: utf-8 -*-

"""This module contains the main handler of the application.
"""

import web
from . import csrf_protected, db, require_login, render, get_session


class WarehouseData:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="")
        session = get_session()
        countries = db.query("SELECT id, name FROM countries ORDER BY name")
        nda_samples = 0
        unbs_samples = 0
        if params.ed:
            res = db.query(
                "SELECT * FROM national_deliery_log WHERE id = $id", {'id': params.ed})
            if res:
                r = res[0]
                po_number, funding_source, manufacturer = (r.po_number, r.funding_source, r.manufacturer)
                made_in, batch_number, nets_type = (r.made_in, r.batch_number, r.nets_type)
                nets_color, nets_size, quantity = (r.nets_color, r.nets_size, r.quantity_bales)
                entry_date, waybill, warehouse = (r.entry_date, r.waybill, r.warehouse)
                sub_warehouse, nda_samples, unbs_samples = (r.sub_warehouse, r.nda_samples, r.unbs_samples)
                nda_sampling_date, nda_testing_result_date = (r.nda_sampling_date, r.nda_testing_result_date)
                nda_conditional_release_date = r.nda_conditional_release_date
                remarks = r.remarks
        if params.d_id:
            if session.role in ('Warehouse Manager', 'Administrator'):
                db.query("DELETE FROM national_deliery_log WHERE id = $id", {'id': params.d_id})

        warehousedata = db.query("SELECT * FROM national_deliery_log")

        l = locals()
        del l['self']
        return render.warehousedata(**l)

    @csrf_protected
    @require_login
    def POST(self):
        params = web.input(
            page=1, ed="", d_id="", po_number="", funding_source="", manufacturer="",
            made_in="", batch_number="", nets_type="", nets_color="", nets_size="",
            quantity="", waybill="", warehouse="", sub_warehouse="", entry_date="",
            nda_samples="", nda_sampling_date="", nda_conditional_release_date="",
            nda_testing_result_date="", unbs_samples="", unbs_sampling_date="",
            remarks=""
        )

        with db.transaction():
            if params.ed:
                pass
            else:
                db.query(
                    "INSERT INTO national_deliery_log (po_number, funding_source, manufacturer, "
                    "made_in, batch_number, nets_type, nets_size, nets_color, quantity_bales, "
                    "entry_date, waybill, warehouse, sub_warehouse, nda_samples, nda_sampling_date, "
                    "nda_conditional_release_date, nda_testing_result_date, unbs_samples, "
                    "unbs_sampling_date, remarks) "
                    "VALUES ($po_number, $funding_source, $manufacturer, "
                    "$made_in, $batch_number, $nets_type, $nets_size, $nets_color, $quantity, "
                    "$entry_date, $waybill, $warehouse, $sub_warehouse, $nda_samples, "
                    "$nda_sampling_date, $nda_crdate, $nda_trdate, $unbs_samples, "
                    "$unbs_sdate, $remarks)", {
                        'po_number': params.po_number, 'funding_source': params.funding_source,
                        'manufacturer': params.manufacturer, 'made_in': params.made_in,
                        'batch_number': params.batch_number, 'nets_type': params.nets_type,
                        'nets_color': params.nets_color, 'nets_size': params.nets_size,
                        'quantity': params.quantity, 'entry_date': params.entry_date,
                        'waybill': params.waybill, 'warehouse': params.warehouse,
                        'sub_warehouse': params.sub_warehouse, 'nda_samples': params.nda_samples,
                        'nda_sampling_date': None if not params.nda_sampling_date else params.nda_sampling_date,
                        'nda_crdate': None if not params.nda_conditional_release_date else params.nda_conditional_release_date,
                        'nda_trdate': None if not params.nda_testing_result_date else params.nda_testing_result_date,
                        'unbs_samples': params.unbs_samples,
                        'unbs_sdate': None if not params.unbs_sampling_date else params.unbs_sampling_date,
                        'remarks': params.remarks
                    })
                return web.seeother("/warehousedata")
        l = locals()
        del l['self']
        return render.warehousedata(**l)
