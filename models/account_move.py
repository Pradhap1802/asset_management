from odoo import models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        """
        Extend _post: sync to asset.management when a depreciation move is posted.
        """
        posted = super()._post(soft=soft)

        depreciation_moves = posted.filtered(
            lambda m: m.asset_id
            and m.asset_move_type == 'depreciation'
            and m.asset_id.asset_management_id
            and m.depreciation_value
        )
        for move in depreciation_moves:
            move.asset_id._sync_depreciation_entries(move.asset_id.asset_management_id)

        return posted

    @api.model_create_multi
    def create(self, vals_list):
        """
        Extend create: when new depreciation moves are created (draft board),
        sync them immediately so the schedule appears in asset.management.
        """
        moves = super().create(vals_list)

        depreciation_moves = moves.filtered(
            lambda m: m.asset_id
            and m.asset_move_type == 'depreciation'
            and m.asset_id.asset_management_id
            and m.depreciation_value
        )
        for move in depreciation_moves:
            move.asset_id._sync_depreciation_entries(move.asset_id.asset_management_id)

        return moves

