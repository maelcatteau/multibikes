from odoo import models, fields
from odoo.exceptions import UserError


class StockPickingUnlockWizard(models.TransientModel):
    _name = 'stock.picking.unlock.wizard'
    _description = 'Wizard pour déverrouiller les transferts de période'

    picking_id = fields.Many2one('stock.picking', string='Transfert', required=True)
    password = fields.Char(string='Mot de passe de déverrouillage', required=True, password=True)
    picking_name = fields.Char(related='picking_id.name', readonly=True)
    picking_origin = fields.Char(related='picking_id.origin', readonly=True)

    def action_unlock_transfer(self):
        """Déverrouiller le transfert après vérification du mot de passe"""
        # Vérifier le mot de passe
        if self.password != "ADMIN_OVERRIDE_2024":
            raise UserError("❌ Mot de passe incorrect. Déverrouillage refusé.")

        # Déverrouiller le transfert
        self.picking_id.with_context(admin_override=True).write({
            'is_period_transfer': False,
            'note': f"🔓 Déverrouillé manuellement le {fields.Datetime.now()} par {self.env.user.name}"
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Transfert déverrouillé',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'target': 'current',  # Remplace la vue actuelle (ferme le wizard)
            'context': {
                'show_notification': {
                    'title': '🔓 Transfert déverrouillé',
                    'message': f'Le transfert {self.picking_id.name} peut maintenant être modifié',
                    'type': 'success',
                }
            }
        }

    def action_cancel(self):
        """Annuler l'opération"""
        return {'type': 'ir.actions.act_window_close'}
