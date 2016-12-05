# -*- coding: utf-8 -*-

"""This module contains the main handler of the application.
"""

import web
from . import csrf_protected, db, require_login, render, get_session
from settings import QUANTITY_PER_BALE
from app.tools.utils import audit_log
import json


class WarehouseData:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="")
        session = get_session()
        countries = db.query("SELECT id, name FROM countries ORDER BY name")
        warehouses = db.query("SELECT id, name FROM warehouses ORDER BY name")
        manufacturers = db.query("SELECT id, name FROM manufacturers ORDER by name")
        funding_sources = db.query("SELECT id, name FROM funding_sources ORDER by name")
        nda_samples = 0
        unbs_samples = 0
        allow_edit = False
        try:
            edit_val = int(params.ed)
            allow_edit = True
        except ValueError:
            pass
        if params.ed and allow_edit:
            res = db.query(
                "SELECT * FROM national_delivery_log WHERE id = $id", {'id': params.ed})
            if res:
                r = res[0]
                po_number, funding_source, manufacturer = (r.po_number, r.funding_source, r.manufacturer)
                made_in, batch_number, nets_type = (r.made_in, r.batch_number, r.nets_type)
                nets_color, nets_size, quantity = (r.nets_color, r.nets_size, r.quantity_bales)
                entry_date, waybill, warehouse_branch = (r.entry_date, r.waybill, r.warehouse_branch)
                sub_warehouse, nda_samples, unbs_samples = (r.sub_warehouse, r.nda_samples, r.unbs_samples)
                nda_sampling_date, nda_testing_result_date = (r.nda_sampling_date, r.nda_testing_result_date)
                nda_conditional_release_date = r.nda_conditional_release_date
                unbs_samples, unbs_sampling_date = (r.unbs_samples, r.unbs_sampling_date)
                remarks = r.remarks
                goods_received_note = r.goods_received_note
                # block a None from being put in date fields
                entry_date = entry_date or ''
                nda_sampling_date = nda_sampling_date or ''
                nda_testing_result_date = nda_testing_result_date or ''
                nda_conditional_release_date = nda_conditional_release_date or ''
                unbs_sampling_date = unbs_sampling_date or ''
                wx = db.query(
                    "SELECT id FROM warehouses WHERE id = "
                    "(SELECT warehouse_id FROM warehouse_branches "
                    " WHERE id = $branch) ", {'branch': warehouse_branch})
                warehouse = wx[0]['id']
                branches = []
                if warehouse:
                    branches = db.query(
                        "SELECT id, name FROM warehouse_branches WHERE warehouse_id = "
                        "$wid", {'wid': warehouse})

        allow_del = False
        try:
            del_val = int(params.d_id)
            allow_del = True
        except ValueError:
            pass
        if params.d_id and allow_del:
            if session.role in ('Warehouse Manager', 'Administrator'):
                res = db.query(
                    "SELECT id, waybill, quantity_bales FROM national_delivery_log "
                    " WHERE id = $id", {'id': params.d_id})
                if res:
                    data = res[0]
                    log_dict = {
                        'logtype': 'Web', 'action': 'Delete', 'actor': session.username,
                        'ip': web.ctx['ip'],
                        'descr': 'Delete warehouse data id:%s, Waybill:%s, Qty (bales):%s' % (
                            data['id'], data['waybill'], data['quantity_bales']),
                        'user': session.sesid
                    }
                    db.query("DELETE FROM national_delivery_log WHERE id = $id", {'id': params.d_id})
                    audit_log(db, log_dict)
                    if params.caller == "api":  # return json if API call
                        web.header("Content-Type", "application/json; charset=utf-8")
                        return json.dumps({'message': "success"})

        warehousedata = db.query("SELECT * FROM national_delivery_log_view ORDER BY id DESC")

        l = locals()
        del l['self']
        return render.warehousedata(**l)

    @csrf_protected
    @require_login
    def POST(self):
        session = get_session()
        params = web.input(
            page=1, ed="", d_id="", po_number="", funding_source="", manufacturer="",
            made_in="", batch_number="", nets_type="", nets_color="", nets_size="",
            quantity="", waybill="", warehouse_branch="", sub_warehouse="", entry_date="",
            nda_samples="", nda_sampling_date="", nda_conditional_release_date="",
            nda_testing_result_date="", unbs_samples="", unbs_sampling_date="",
            remarks="", goods_received_note=""
        )
        allow_edit = False
        try:
            edit_val = int(params.ed)
            allow_edit = True
        except ValueError:
            pass

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
            if params.ed and allow_edit:
                r = db.query(
                    "UPDATE national_delivery_log SET po_number=$po_number, funding_source=$funding_source, "
                    "manufacturer=$manufacturer, made_in=$made_in, batch_number=$batch_number, "
                    "nets_type=$nets_type, nets_size=$nets_size, nets_color=$nets_color, "
                    "quantity_bales=$quantity, entry_date=$entry_date, waybill=$waybill, "
                    "warehouse_branch=$branch, sub_warehouse=$sub_warehouse, nda_samples=$nda_samples, "
                    "nda_sampling_date=$nda_sampling_date, "
                    "nda_conditional_release_date=$nda_crdate, nda_testing_result_date=$nda_trdate, "
                    "unbs_samples=$unbs_samples, unbs_sampling_date=$unbs_sdate, remarks = $remarks, "
                    "goods_received_note=$grn, created_by=$user, quantity=$total "
                    " WHERE id = $id RETURNING id", {
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
                        'user': session.sesid, 'total': total_nets, 'id': params.ed
                    })

                if r:
                    data_id = r[0]['id']
                    log_dict = {
                        'logtype': 'Warehouse', 'action': 'Update', 'actor': session.username,
                        'ip': web.ctx['ip'],
                        'descr': 'Updated warehouse data id:%s, Waybill:%s, Qty (bales):%s' % (
                            data_id, params.waybill, params.quantity),
                        'user': session.sesid
                    }
                    audit_log(db, log_dict)
                return web.seeother("/warehousedata")
            else:
                has_entry = db.query(
                    "SELECT id FROM national_delivery_log WHERE waybill=$waybill "
                    "OR goods_received_note = $grn",
                    {'waybill': params.waybill, 'grn': params.goods_received_note})
                if has_entry:
                    session.wdata_err = (
                        "Entry with Waybill:%s OR Goods Received Note:%s "
                        "already entered" % (params.waybill, params.goods_received_note))
                    return web.seeother("/warehousedata")
                session.wdata_err = ""
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
                        'user': session.sesid, 'total': total_nets
                    })

                if r:
                    data_id = r[0]['id']
                    log_dict = {
                        'logtype': 'Warehouse', 'action': 'Create', 'actor': session.username,
                        'ip': web.ctx['ip'],
                        'descr': 'Added warehouse data entry id:%s, Waybill:%s, Qty (bales):%s' % (
                            data_id, params.waybill, params.quantity),
                        'user': session.sesid
                    }
                    audit_log(db, log_dict)
                return web.seeother("/warehousedata")
        l = locals()
        del l['self']
        return render.warehousedata(**l)
