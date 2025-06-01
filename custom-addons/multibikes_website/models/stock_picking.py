# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # === Champs ===
    is_period_transfer = fields.Boolean(
        string="Transfert de période",
        default=False,
        help="Indique si ce transfert fait partie d'un transfert saisonnier automatique",
        copy=False,
        readonly=True  # Protégé dans l'interface
    )
    
    period_config_id = fields.Many2one(
        'mb_renting_period',
        string="Configuration de période",
        help="Configuration de période associée à ce transfert",
        copy=False,
        ondelete='set null',
        readonly=True  # Protégé dans l'interface
    )

    # === Protection avec clause d'urgence ===
    
    def _check_period_transfer_immutability(self):
        """
        Verrouillage avec possibilité de déverrouillage temporaire
        """
        period_transfers = self.filtered('is_period_transfer')
        if period_transfers:
            transfer_names = period_transfers.mapped('name')
            raise UserError(
                "🚫 TRANSFERTS DE PÉRIODE VERROUILLÉS 🚫\n\n"
                f"Transferts protégés :\n• {chr(10).join(transfer_names)}\n\n"
                "❌ Ces transferts ne peuvent pas être modifiés\n"
                "✅ Ils sont gérés automatiquement par le système saisonnier\n\n"
                "⚠️  Contactez le développeur pour une intervention d'urgence"
            )

    def write(self, vals):
        """
        Protection avec clause de déverrouillage temporaire
        """
        # Clause d'urgence : déverrouillage temporaire
        if self.env.context.get('admin_override'):
            return super(StockPicking, self).write(vals)
            
        # Protection normale
        self._check_period_transfer_immutability()
        
        return super().write(vals)

    def unlink(self):
        """
        Protection contre la suppression avec clause d'urgence
        """
        # Clause d'urgence
        if self.env.context.get('admin_override'):
            return super(StockPicking, self).unlink()
            
        # Protection normale
        self._check_period_transfer_immutability()
        
        return super().unlink()

    # === Méthode d'urgence cachée ===
    
    def _emergency_admin_override(self, confirmation_code, action_vals):
        """
        Méthode d'urgence pour modifications temporaires
        
        :param confirmation_code: Code de confirmation
        :param action_vals: Dictionnaire des valeurs à modifier
        :return: Résultat de l'opération
        """
        if confirmation_code != "ADMIN_OVERRIDE_2024":
            raise UserError("Code de confirmation incorrect")
            
        # Modification avec bypass temporaire
        return self.with_context(admin_override=True).write(action_vals)
    
    # === Contrainte de cohérence ===
    
    @api.constrains('is_period_transfer', 'period_config_id')
    def _check_period_config_consistency(self):
        """
        Vérification de cohérence
        """
        for picking in self:
            if picking.is_period_transfer and not picking.period_config_id:
                raise UserError(
                    f"Le transfert de période {picking.name} doit avoir "
                    "une configuration de période associée."
                )
