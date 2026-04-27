from odoo import models, fields, api, _, exceptions


class AssetDisposal(models.Model):
    _name = 'asset.disposal'
    _description = 'Asset Disposal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'disposal_date desc, id desc'

    # -------------------------------------------------------------------------
    # Core fields
    # -------------------------------------------------------------------------
    name = fields.Char(
        string="Disposal Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    asset_id = fields.Many2one(
        'asset.management',
        string="Asset",
        required=True,
        ondelete='cascade',
        tracking=True,
        help="The asset being disposed / scrapped",
    )
    product_id = fields.Many2one(
        'product.product',
        string="Product",
        related='asset_id.product_id',
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string="Branch",
        related='asset_id.company_id',
        store=True,
        readonly=True,
    )
    asset_type_id = fields.Many2one(
        'asset.type',
        string="Asset Type",
        related='asset_id.asset_type_id',
        store=True,
        readonly=True,
    )
    serial_number_ids = fields.Many2many(
        'asset.serial.number',
        'asset_disposal_serial_rel',
        'disposal_id',
        'serial_id',
        string="Serial Numbers",
        help="Select the specific serial numbers being disposed / scrapped",
    )

    # -------------------------------------------------------------------------
    # Disposal details
    # -------------------------------------------------------------------------
    disposal_date = fields.Date(
        string="Disposal Date",
        default=fields.Date.today,
        required=True,
        tracking=True,
        help="Date the asset was disposed / scrapped",
    )
    disposal_method = fields.Selection([
        ('scrap', 'Scrap'),
        ('sold', 'Sold'),
        ('donated', 'Donated'),
        ('written_off', 'Written Off'),
        ('other', 'Other'),
    ], string="Disposal Method", default='scrap', required=True, tracking=True)

    disposal_value = fields.Float(
        string="Disposal / Sale Value",
        help="Amount realised from selling or scrapping the asset (0 for scrap/write-off)",
        tracking=True,
    )
    book_value_at_disposal = fields.Float(
        string="Book Value at Disposal",
        help="Net book value of the asset at the time of disposal",
    )
    loss_on_disposal = fields.Float(
        string="Loss / (Gain) on Disposal",
        compute='_compute_loss_on_disposal',
        store=True,
        help="Positive = loss, Negative = gain",
    )

    disposal_reason = fields.Text(
        string="Reason for Disposal",
        tracking=True,
        help="Explain why the asset is being disposed",
    )
    approved_by = fields.Many2one(
        'res.users',
        string="Approved By",
        default=lambda self: self.env.user,
        tracking=True,
    )

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Disposed'),
    ], string="Status", default='draft', tracking=True)

    # -------------------------------------------------------------------------
    # Computed
    # -------------------------------------------------------------------------
    @api.depends('book_value_at_disposal', 'disposal_value')
    def _compute_loss_on_disposal(self):
        for rec in self:
            rec.loss_on_disposal = rec.book_value_at_disposal - rec.disposal_value

    @api.onchange('asset_id')
    def _onchange_asset_id(self):
        """Automatically fetch the current book value when the asset is selected."""
        if self.asset_id:
            self.book_value_at_disposal = self.asset_id.current_amount

    # -------------------------------------------------------------------------
    # ORM
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('asset.disposal') or 'New'
                )
            # Ensure the book value is captured upon creation if omitted
            if 'book_value_at_disposal' not in vals and vals.get('asset_id'):
                asset = self.env['asset.management'].browse(vals['asset_id'])
                vals['book_value_at_disposal'] = asset.current_amount
        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def action_confirm(self):
        for rec in self:
            if rec.state == 'draft':
                rec.state = 'confirmed'

    def action_done(self):
        for rec in self:
            if rec.state == 'confirmed':
                rec.state = 'done'
                # Ensure the linked asset is marked expired/scrap
                if rec.asset_id.asset_status != 'expired':
                    rec.asset_id.asset_status = 'expired'

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'
