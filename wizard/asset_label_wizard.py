from odoo import models, fields, api, exceptions, _


class AssetLabelLayout(models.TransientModel):
    _name = 'asset.label.layout'
    _description = 'Choose the sheet layout to print the asset labels'

    print_format = fields.Selection([
        ('dymo', 'Dymo'),
        ('2x7xprice', '2 x 7 with price'),
        ('4x7xprice', '4 x 7 with price'),
        ('4x12', '4 x 12'),
        ('4x12xprice', '4 x 12 with price'),
        ('custom', 'Custom Columns')], 
        string="Format", default='2x7xprice', required=True)
    custom_quantity = fields.Integer('Quantity', default=1, required=True)
    asset_ids = fields.Many2many('asset.management', string='Assets')
    custom_columns = fields.Integer('Number of Columns', default=2, required=True,
                                    help="Number of columns per page (e.g., 2 for 2 columns)")
    custom_rows = fields.Integer('Number of Rows', default=7, required=True,
                                help="Number of rows per page (e.g., 7 for 7 rows)")
    show_price = fields.Boolean('Show Price', default=True, 
                               help="Display asset price on labels")
    red_band_color = fields.Char('Label Header Color', default='#dc3545', 
                                help="Color for the top header band on labels. Enter a hex color code (e.g., #dc3545 for red, #015f7b for blue)")
    rows = fields.Integer(compute='_compute_dimensions')
    columns = fields.Integer(compute='_compute_dimensions')

    @api.depends('print_format', 'custom_columns', 'custom_rows')
    def _compute_dimensions(self):
        for wizard in self:
            if wizard.print_format == 'custom':
                wizard.columns = wizard.custom_columns
                wizard.rows = wizard.custom_rows
            elif 'x' in wizard.print_format:
                columns, rows = wizard.print_format.split('x')[:2]
                wizard.columns = columns.isdigit() and int(columns) or 1
                wizard.rows = rows.isdigit() and int(rows) or 1
            else:
                wizard.columns, wizard.rows = 1, 1

    def _prepare_report_data(self):
        if self.custom_quantity <= 0:
            raise exceptions.UserError(_('You need to set a positive quantity.'))

        if self.print_format == 'custom':
            if self.custom_columns <= 0 or self.custom_rows <= 0:
                raise exceptions.UserError(_('Columns and rows must be greater than zero.'))
            # Use custom template for custom columns
            xml_id = 'asset_management.report_asset_template_label_custom'
        elif self.print_format == 'dymo':
            xml_id = 'asset_management.report_asset_template_label_dymo'
        elif 'x' in self.print_format:
            xml_id = 'asset_management.report_asset_template_label_%sx%s' % (self.columns, self.rows)
            if 'xprice' not in self.print_format:
                xml_id += '_noprice'
        else:
            xml_id = ''

        if not self.asset_ids:
            raise exceptions.UserError(_("No asset to print. Please select at least one asset."))

        # Build data to pass to the report - always include price
        price_included = True  # Always show price on labels
        data = {
            'active_model': 'asset.management',
            'quantity_by_asset': {asset.id: self.custom_quantity for asset in self.asset_ids},
            'layout_wizard': self.id,
            'price_included': price_included,
            'custom_columns': self.columns if self.print_format == 'custom' else None,
            'custom_rows': self.rows if self.print_format == 'custom' else None,
            'red_band_color': self.red_band_color or '#dc3545',
        }
        return xml_id, data

    def process(self):
        self.ensure_one()
        xml_id, data = self._prepare_report_data()
        if not xml_id:
            raise exceptions.UserError(_('Unable to find report template for %s format', self.print_format))
        report_action = self.env.ref(xml_id).report_action(None, data=data, config=False)
        report_action.update({'close_on_report_download': True})
        return report_action

    @api.model
    def default_get(self, fields_list):
        """Set default assets from context (active_ids)"""
        res = super(AssetLabelLayout, self).default_get(fields_list)
        if self.env.context.get('active_ids'):
            res['asset_ids'] = [(6, 0, self.env.context.get('active_ids'))]
        return res

