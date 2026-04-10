# -*- coding: utf-8 -*-
from collections import defaultdict
from odoo import models


def _prepare_data(env, docids, data):
    """Prepare data for asset label reports - Odoo 18 version"""
    layout_wizard = env['asset.label.layout'].browse(data.get('layout_wizard'))
    Asset = env['asset.management']
    
    if not layout_wizard:
        return {}

    total = 0
    qty_by_asset_in = data.get('quantity_by_asset')
    # Search for assets all at once, ordered by name desc
    assets = Asset.search([('id', 'in', [int(a) for a in qty_by_asset_in.keys()])], order='name desc')
    quantity_by_asset = defaultdict(list)
    
    for asset in assets:
        q = qty_by_asset_in[str(asset.id)]
        # Use barcode if available, otherwise use asset name as barcode
        barcode_value = asset.barcode if asset.barcode else asset.name
        quantity_by_asset[asset].append((barcode_value, q))
        total += q

    # Get custom dimensions if provided
    custom_columns = data.get('custom_columns')
    custom_rows = data.get('custom_rows')
    
    # Use custom dimensions if provided, otherwise use wizard dimensions
    columns = custom_columns if custom_columns else layout_wizard.columns
    rows = custom_rows if custom_rows else layout_wizard.rows
    
    # Get red band color from data, default to #dc3545
    red_band_color = data.get('red_band_color', '#dc3545')
    
    return {
        'quantity': quantity_by_asset,
        'page_numbers': (total - 1) // (rows * columns) + 1 if (rows * columns) > 0 else 1,
        'price_included': data.get('price_included'),
        'columns': columns,
        'rows': rows,
        'red_band_color': red_band_color,
    }


class ReportAssetTemplateLabel2x7(models.AbstractModel):
    _name = 'report.asset_management.report_assettemplatelabel2x7'
    _description = 'Asset Label Report 2x7'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, docids, data)


class ReportAssetTemplateLabel4x7(models.AbstractModel):
    _name = 'report.asset_management.report_assettemplatelabel4x7'
    _description = 'Asset Label Report 4x7'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, docids, data)


class ReportAssetTemplateLabel4x12(models.AbstractModel):
    _name = 'report.asset_management.report_assettemplatelabel4x12'
    _description = 'Asset Label Report 4x12'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, docids, data)


class ReportAssetTemplateLabel4x12NoPrice(models.AbstractModel):
    _name = 'report.asset_management.report_assettemplatelabel4x12noprice'
    _description = 'Asset Label Report 4x12 No Price'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, docids, data)


class ReportAssetTemplateLabelDymo(models.AbstractModel):
    _name = 'report.asset_management.report_assettemplatelabel_dymo'
    _description = 'Asset Label Report Dymo'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, docids, data)


class ReportAssetTemplateLabelCustom(models.AbstractModel):
    _name = 'report.asset_management.report_assettemplatelabel_custom'
    _description = 'Asset Label Report Custom Columns'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, docids, data)

