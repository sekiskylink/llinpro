# -*- coding: utf-8 -*-

"""This module contains the main handler of the application.
"""

import web
from . import db, render
from settings import QUANTITY_PER_BALE
from app.tools.utils import audit_log
import json


class WarehouseDataAPI:
    def POST(self):
        params = web.input(
            page=1, ed="", d_id="", po_number="", funding_source="", manufacturer="",
            made_in="", batch_number="", nets_type="", nets_color="", nets_size="",
            quantity="0", waybill="", warehouse_branch="", sub_warehouse="", entry_date="",
            nda_samples="0", nda_sampling_date="", nda_conditional_release_date="",
            nda_testing_result_date="", unbs_samples="0", unbs_sampling_date="",
            remarks="", goods_received_note="", caller='web', user=''
        )
        print web.data()
        userid = 0
        user = db.query("SELECT id FROM users WHERE username = $user", {'user': params.user})
        if user:
            userid = user[0]['id']

        with db.transaction():
            nda_samples = 0
            unbs_samples = 0
            try:
                nda_samples = int(params.nda_samples)
                unbs_samples = int(params.unbs_samples)
                quantity = int(params.quantity)
            except:
                pass
            total_nets = (quantity * QUANTITY_PER_BALE) - (nda_samples + unbs_samples)

            has_entry = db.query(
                "SELECT id FROM national_delivery_log WHERE waybill=$waybill "
                "AND goods_received_note = $grn",
                {'waybill': params.waybill, 'grn': params.goods_received_note})
            if has_entry:
                return json.dumps({
                    'status': 'FAILED', 'messsage':
                    'Waybill or GRN Already Exists [%s: %s]' % (params.waybill, params.goods_received_note)})
            r = db.query(
                "INSERT INTO national_delivery_log (po_number, funding_source, manufacturer, "
                "made_in, batch_number, nets_type, nets_size, nets_color, quantity_bales, "
                "entry_date, waybill, warehouse_branch, sub_warehouse, nda_samples, nda_sampling_date, "
                "nda_conditional_release_date, nda_testing_result_date, unbs_samples, "
                "unbs_sampling_date, remarks, goods_received_note, created_by, quantity) "
                "VALUES ($po_number, $funding_source, $manufacturer, "
                "$made_in, $batch_number, $nets_type, $nets_size, $nets_color, $quantity, "
                "$entry_date, $waybill, $branch, $sub_warehouse, $nda_samples, "
                "$nda_sampling_date, $nda_crdate, $nda_trdate, $unbs_samples, "
                "$unbs_sdate, $remarks, $grn, $user, $total) RETURNING id", {
                    'po_number': params.po_number, 'funding_source': params.funding_source,
                    'manufacturer': params.manufacturer, 'made_in': params.made_in,
                    'batch_number': params.batch_number, 'nets_type': params.nets_type,
                    'nets_color': params.nets_color, 'nets_size': params.nets_size,
                    'quantity': params.quantity, 'entry_date': params.entry_date,
                    'waybill': params.waybill, 'branch': params.warehouse_branch,
                    'sub_warehouse': params.sub_warehouse, 'nda_samples': params.nda_samples,
                    'nda_sampling_date': None if not params.nda_sampling_date else params.nda_sampling_date,
                    'nda_crdate': None if not params.nda_conditional_release_date else params.nda_conditional_release_date,
                    'nda_trdate': None if not params.nda_testing_result_date else params.nda_testing_result_date,
                    'unbs_samples': params.unbs_samples,
                    'unbs_sdate': None if not params.unbs_sampling_date else params.unbs_sampling_date,
                    'remarks': params.remarks, 'grn': params.goods_received_note,
                    'user': userid if userid else 1, 'total': total_nets
                })

            if r:
                data_id = r[0]['id']
                log_dict = {
                    'logtype': 'Warehouse', 'action': 'Create', 'actor': params.user,
                    'ip': web.ctx['ip'],
                    'descr': 'Added warehouse data entry id:%s, Waybill:%s, GRN:%s, Qty (bales):%s' % (
                        data_id, params.waybill, params.goods_received_note, params.quantity),
                    'user': userid if userid else 1
                }
                audit_log(db, log_dict)
                return json.dumps({'status': 'SUCCESS', 'message': 'successfully added!'})
        return render.warehousedata({
            'status': 'FAILED', 'message': 'Not Added [%s: %s]' % (params.waybill, params.goods_received_note)})
