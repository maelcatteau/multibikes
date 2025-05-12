# -*- coding: utf-8 -*-
"""
Module de prolongation de location pour Multibikes
-------------------------------------------------
Ce module permet de prolonger les locations existantes en créant de nouvelles commandes
liées aux commandes de location d'origine. Il offre un assistant permettant de sélectionner
les articles à prolonger et de définir la nouvelle période de location.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class RentalExtensionWizardLine(models.TransientModel):
    """
    Lignes de l'assistant de prolongation de location
    -----------------------------------------------
    Cette classe représente les lignes du wizard de prolongation, permettant
    de sélectionner les articles à prolonger et leurs quantités.
    """
    _name = 'rental.extension.wizard.line'
    _description = "Lignes de l'assistant de prolongation de location"
    
    mb_wizard_id = fields.Many2one('rental.extension.wizard', string="Assistant", required=True, ondelete='cascade')
    mb_order_line_id = fields.Many2one('sale.order.line', string="Ligne de commande originale", required=True)
    mb_product_id = fields.Many2one('product.product', string="Produit", required=True)
    mb_product_name = fields.Char(string="Description", required=True)
    mb_quantity = fields.Float(string="Quantité", required=True, default=1.0)
    mb_uom_id = fields.Many2one('uom.uom', string="Unité de mesure", required=True)
    mb_selected = fields.Boolean(string="Sélectionné", default=True, 
                              help="Cochez cette case pour inclure ce produit dans la prolongation")
    mb_available_qty = fields.Float(string="Quantité disponible", compute='_compute_available_qty', 
                               help="Quantité disponible pour prolongation (livrée mais pas encore retournée)")
    
    @api.depends('mb_order_line_id')
    def _compute_available_qty(self):
        """
        Calcule la quantité disponible pour prolongation
        ----------------------------------------------
        La quantité disponible est la différence entre la quantité livrée
        et la quantité déjà retournée pour chaque ligne de commande.
        """
        for line in self:
            if line.mb_order_line_id:
                line.mb_available_qty = line.mb_order_line_id.qty_delivered - line.mb_order_line_id.qty_returned
                _logger.debug(
                    "Calcul quantité disponible: produit=%s, ligne=%s, livrée=%s, retournée=%s, disponible=%s",
                    line.mb_product_id.name, line.mb_order_line_id.id,
                    line.mb_order_line_id.qty_delivered, line.mb_order_line_id.qty_returned, line.mb_available_qty
                )
            else:
                line.mb_available_qty = 0.0
    
    @api.onchange('mb_quantity')
    def _onchange_quantity(self):
        """
        Vérifie que la quantité ne dépasse pas la quantité disponible
        -----------------------------------------------------------
        Cette validation empêche l'utilisateur de prolonger plus d'articles
        que ce qui est actuellement en location (non retourné).
        
        Raises:
            UserError: Si la quantité saisie dépasse la quantité disponible
        """
        for line in self:
            if line.mb_quantity > line.mb_available_qty:
                _logger.warning(
                    "Tentative de prolongation avec quantité excessive: produit=%s, demandé=%s, disponible=%s",
                    line.mb_product_id.name, line.mb_quantity, line.mb_available_qty
                )
                raise UserError(_(
                    "Vous ne pouvez pas prolonger plus de %s unités pour l'article %s. "
                    "Cette quantité correspond aux articles actuellement en location (non retournés)."
                ) % (line.mb_available_qty, line.mb_product_id.name))
