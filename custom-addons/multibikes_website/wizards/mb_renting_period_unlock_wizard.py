from odoo import models, fields
from odoo.exceptions import UserError


class MbRentingPeriodUnlockWizard(models.TransientModel):
    _name = 'mb.renting.period.unlock.wizard'
    _description = 'Wizard pour déverrouiller une période confirmée'

    period_id = fields.Many2one('mb.renting.period', string='Période', required=True)
    password = fields.Char(string='Mot de passe de déverrouillage', required=True, password=True)
    period_name = fields.Char(related='period_id.name', readonly=True)
    period_state = fields.Selection(related='period_id.state', readonly=True)

    def action_unlock_period(self):
        """Déverrouiller la période après vérification du mot de passe"""
        # Vérifier le mot de passe
        if self.password != "ADMIN_OVERRIDE_2024":
            raise UserError("❌ Mot de passe incorrect. Déverrouillage refusé.")

        # Déverrouiller la période (remettre en brouillon)
        self.period_id.with_context(admin_override=True).write({
            'state': 'draft'
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Période déverrouillée',
            'res_model': 'mb.renting.period',
            'res_id': self.period_id.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'show_notification': {
                    'title': '🔓 Période déverrouillée',
                    'message': f'La période {self.period_id.name} peut maintenant être modifiée',
                    'type': 'success',
                }
            }
        }

    def action_cancel(self):
        """Annuler l'opération"""
        return {'type': 'ir.actions.act_window_close'}
