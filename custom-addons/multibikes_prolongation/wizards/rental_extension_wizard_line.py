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
from odoo.tools.float_utils import float_compare
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
    mb_product_id = fields.Many2one('product.product', string="Produit à prolonger", required=True)
    mb_product_name = fields.Char(string="Description", required=True)
    mb_quantity = fields.Float(string="Quantité en prolongation", required=True, default=1.0)
    mb_uom_id = fields.Many2one('uom.uom', string="Unité de mesure de prolongation", required=True)
    mb_selected = fields.Boolean(string="Sélectionné", default=True, 
                              help="Cochez cette case pour inclure ce produit dans la prolongation")
    mb_available_qty = fields.Float(string="Quantité disponible", compute='_compute_available_qty', 
                               help="Quantité disponible pour prolongation (livrée mais pas encore retournée)")
    
    # Champs nécessaires pour le widget qty_at_date_widget
    virtual_available_at_date = fields.Float(string='Quantité prévue', compute='_compute_qty_at_date')
    qty_available_today = fields.Float(string='Quantité disponible aujourd\'hui', compute='_compute_qty_at_date')
    free_qty_today = fields.Float(string='Quantité libre aujourd\'hui', compute='_compute_qty_at_date')
    scheduled_date = fields.Datetime(string="Date planifiée", compute='_compute_qty_at_date')
    forecast_expected_date = fields.Datetime(string="Date prévue", compute='_compute_qty_at_date')
    warehouse_id = fields.Many2one('stock.warehouse', string="Entrepôt", compute='_compute_qty_at_date')
    move_ids = fields.One2many('stock.move', string="Mouvements de stock", compute='_compute_qty_at_date')
    qty_to_deliver = fields.Float(string="Quantité à livrer", compute='_compute_qty_at_date')
    is_mto = fields.Boolean(string="Produit à la commande", compute='_compute_qty_at_date')
    display_qty_widget = fields.Boolean(string="Afficher le widget de quantité", default=True)
    product_id = fields.Many2one('product.product', string="Produit original", compute='_compute_product_data')
    product_uom = fields.Many2one('uom.uom', string="Unité de mesure originale", compute='_compute_product_data')
    product_uom_qty = fields.Float(string="Quantité originale", compute='_compute_product_data')
    
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
    
    @api.depends('mb_order_line_id')
    def _compute_product_data(self):
        """
        Calcule les données du produit nécessaires pour le widget de quantité
        -------------------------------------------------------------------
        Cette méthode récupère les informations du produit depuis la ligne de commande
        originale pour les utiliser dans le widget de quantité.
        """
        for line in self:
            if line.mb_order_line_id:
                line.product_id = line.mb_order_line_id.product_id
                line.product_uom = line.mb_order_line_id.product_uom
                line.product_uom_qty = line.mb_quantity
            else:
                line.product_id = False
                line.product_uom = False
                line.product_uom_qty = 0.0
    
    @api.depends('mb_wizard_id.mb_start_date', 'product_id', 'mb_order_line_id')
    def _compute_qty_at_date(self):
        """
        Calcule les quantités disponibles à la date prévue
        ------------------------------------------------
        Cette méthode fournit les informations de stock nécessaires pour le widget
        qty_at_date_widget, permettant d'afficher les disponibilités prévisionnelles
        des produits à la date de début de la prolongation.
        """
        for line in self:
            if not line.product_id or not line.mb_wizard_id.mb_start_date:
                # Valeurs par défaut si pas de produit ou date
                line.virtual_available_at_date = 0
                line.qty_available_today = 0
                line.free_qty_today = 0
                line.scheduled_date = False
                line.forecast_expected_date = False
                line.warehouse_id = False
                line.move_ids = [(5, 0, 0)]
                line.qty_to_deliver = 0
                line.is_mto = False
                continue
                
            # Utiliser la logique de calcul de stock similaire à celle de sale.order.line
            scheduled_date = line.mb_wizard_id.mb_start_date
            warehouse = line.mb_order_line_id.order_id.warehouse_id
            
            # Obtenir le stock disponible à la date planifiée
            qty_available = line.product_id.with_context(
                warehouse=warehouse.id,
                to_date=scheduled_date
            ).virtual_available
            
            # Obtenir les quantités actuelles
            product = line.product_id.with_context(warehouse=warehouse.id)
            
            line.warehouse_id = warehouse
            line.scheduled_date = scheduled_date
            line.forecast_expected_date = scheduled_date
            line.virtual_available_at_date = qty_available
            line.qty_available_today = product.qty_available
            line.free_qty_today = product.free_qty
            line.qty_to_deliver = line.product_uom_qty
            line.is_mto = line.product_id.type == 'product' and float_compare(
                line.product_id.nbr_reordering_rules, 0, precision_rounding=line.product_id.uom_id.rounding
            ) > 0
            
            # Trouver les mouvements de stock associés
            moves = self.env['stock.move'].search([
                ('product_id', '=', line.product_id.id),
                ('state', 'not in', ['done', 'cancel']),
                ('date', '<=', scheduled_date),
            ])
            line.move_ids = moves
