# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_rental_extension = fields.Boolean(
        string="Est une prolongation",
        default=False,
        help="Indique si cette commande est une prolongation d'une location existante"
    )
    original_rental_id = fields.Many2one(
        'sale.order',
        string="Location d'origine",
        help="La commande de location d'origine dont celle-ci est une prolongation"
    )
    extension_count = fields.Integer(
        string="Nombre de prolongations",
        compute='_compute_extension_count',
        help="Nombre de prolongations liées à cette location"
    )
    rental_extensions_ids = fields.One2many(
        'sale.order',
        'original_rental_id',
        string="Prolongations de location",
        help="Liste des prolongations liées à cette location"
    )
    
    @api.depends('rental_extensions_ids')
    def _compute_extension_count(self):
        for order in self:
            order.extension_count = len(order.rental_extensions_ids)
    
    def action_extend_rental(self):
        """Ouvre un assistant pour prolonger la location"""
        self.ensure_one()
        
        # Vérifier que c'est bien une location
        if not self.is_rental_order:
            raise UserError(_("Cette commande n'est pas une location."))
        
        # Vérifier que la location est confirmée
        if self.state not in ['sale', 'done']:
            raise UserError(_("La location doit être confirmée avant de pouvoir être prolongée."))
        
        # Préparer les lignes de l'assistant
        wizard_line_vals = []
        for line in self.order_line:
            # Créer une ligne pour chaque produit de la commande
            wizard_line_vals.append((0, 0, {
                'order_line_id': line.id,
                'product_id': line.product_id.id,
                'product_name': line.name,
                'quantity': line.product_uom_qty,
                'uom_id': line.product_uom.id,
                'selected': True,  # Par défaut, tous les produits sont sélectionnés
            }))
        
        # Créer et ouvrir l'assistant
        context = dict(
            self.env.context,
            default_order_id=self.id,
            default_start_date=self.rental_return_date,  # Date de fin actuelle comme date de début de prolongation
        )
        
        # Créer le wizard
        wizard = self.env['rental.extension.wizard'].create({
            'order_id': self.id,
            'start_date': self.rental_return_date,
            'end_date': self.rental_return_date + timedelta(days=1),  # Par défaut, prolongation d'un jour
            'line_ids': wizard_line_vals,
        })
        
        return {
            'name': _('Prolonger la location'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'rental.extension.wizard',
            'res_id': wizard.id,
            'view_id': self.env.ref('multibikes_base.view_rental_extension_wizard_form').id,
            'target': 'new',
            'context': context,
        }
    
    def action_view_extensions(self):
        """Affiche les prolongations liées à cette location"""
        self.ensure_one()
        return {
            'name': _('Prolongations'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'sale.order',
            'domain': [('original_rental_id', '=', self.id)],
            'context': {'create': False}
        }


