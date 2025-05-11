# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class RentalExtensionWizard(models.TransientModel):
    _name = 'rental.extension.wizard'
    _description = "Assistant de prolongation de location"

    order_id = fields.Many2one(
        'sale.order',
        string="Commande de location",
        required=True
    )
    start_date = fields.Datetime(
        string="Date de début de la prolongation",
        required=True,
        help="Par défaut, la date de fin de la location actuelle"
    )
    end_date = fields.Datetime(
        string="Nouvelle date de fin",
        required=True,
        help="Date de fin de la prolongation"
    )
    line_ids = fields.One2many(
        'rental.extension.wizard.line',
        'wizard_id',
        string="Articles à prolonger"
    )
    
    @api.onchange('end_date', 'start_date')
    def _onchange_dates(self):
        """Valider que la date de fin est après la date de début"""
        if self.end_date and self.start_date and self.end_date <= self.start_date:
            raise UserError(_("La date de fin de prolongation doit être postérieure à la date de début."))
    
    def _prepare_extension_order_values(self):
        """Prépare les valeurs pour la création de la commande de prolongation"""
        original_order = self.order_id
        
        # Durée totale de location (original + prolongation)
        original_duration_days = (original_order.rental_return_date - original_order.rental_start_date).days
        extension_duration_days = (self.end_date - self.start_date).days
        total_duration_days = original_duration_days + extension_duration_days
        
        # Copier les valeurs nécessaires de la commande originale
        return {
            'partner_id': original_order.partner_id.id,
            'partner_invoice_id': original_order.partner_invoice_id.id,
            'partner_shipping_id': original_order.partner_shipping_id.id,
            'pricelist_id': original_order.pricelist_id.id,
            'rental_start_date': self.start_date,
            'rental_return_date': self.end_date,
            'is_rental_order': True,
            'is_rental_extension': True,
            'original_rental_id': original_order.id,
            'company_id': original_order.company_id.id,
            'warehouse_id': original_order.warehouse_id.id,
            'client_order_ref': original_order.client_order_ref,
            'note': _("Prolongation de la location %s. Durée totale: %s jours") % 
                   (original_order.name, total_duration_days),
        }
    
    def _prepare_extension_line_values(self, extension_order, wizard_line):
        """Prépare les valeurs pour les lignes de la commande de prolongation"""
        original_line = wizard_line.order_line_id
        product = original_line.product_id
        
        # Calcul de la durée en jours
        start_date = self.start_date
        end_date = self.end_date
        duration_days = (end_date - start_date).days
        
        # Récupérer la catégorie du produit pour appliquer la bonne stratégie de tarification
        category = product.categ_id
        
        # Calcul du prix selon la catégorie de produit
        # Cette logique devra être adaptée selon vos besoins spécifiques
        price_unit = self._calculate_extension_price(product, original_line, duration_days)
        
        # Créer les valeurs de ligne sans inclure order_id si extension_order n'est pas encore créé
        line_vals = {
            'product_id': product.id,
            'product_uom_qty': wizard_line.quantity,
            'product_uom': wizard_line.uom_id.id,
            'price_unit': price_unit,
            'discount': 0,
            'name': _("%s - Prolongation du %s au %s") % (
                product.name,
                start_date.strftime('%d/%m/%Y %H:%M'),
                end_date.strftime('%d/%m/%Y %H:%M')
            ),
            'scheduled_date': start_date,
            'return_date': end_date,
            'is_rental': True,
        }
        
        # Ajouter order_id uniquement si extension_order existe et a un ID
        if extension_order and extension_order.id:
            line_vals['order_id'] = extension_order.id
            
        return line_vals
    
    def _calculate_extension_price(self, product, original_line, duration_days):
        """
        Calcule le prix de la prolongation selon la catégorie du produit
        Cette fonction devra être adaptée selon vos règles de tarification spécifiques
        """
        original_order = self.order_id
        original_duration_days = (original_order.rental_return_date - original_order.rental_start_date).days
        total_duration_days = original_duration_days + duration_days
        
        # Logique de prix basée sur la catégorie de produit
        category = product.categ_id
        
        # Exemple de logique de tarification par catégorie
        # À adapter selon vos besoins spécifiques
        if category.name == 'Vélos':
            if total_duration_days <= 5:
                return original_line.price_unit
            else:
                return 4.5  # 4.5€ par jour pour les jours de prolongation
        elif category.name == 'Accessoires':
            if total_duration_days <= 3:
                return original_line.price_unit
            else:
                return 2.5  # 2.5€ par jour pour les jours de prolongation
        else:
            # Prix par défaut pour les autres catégories
            return original_line.price_unit
    
    def _handle_pickings(self, original_order, extension_order):
        """
        Met à jour les quantités retournées et livrées des lignes de commande
        sans manipuler les bons de livraison/retour
        """
        # Pour chaque ligne du wizard qui a été sélectionnée
        for wizard_line in self.line_ids.filtered(lambda l: l.selected):
            # 1. Marquer comme retourné dans la commande originale
            original_line = wizard_line.order_line_id
            if original_line:
                # Mettre à jour qty_returned pour marquer uniquement la quantité prolongée comme retournée
                # Attention: ne pas dépasser la quantité totale
                prolonged_qty = min(wizard_line.quantity, original_line.product_uom_qty)
                
                # Si la ligne a déjà des retours partiels, on ajoute à la quantité déjà retournée
                new_returned_qty = min(
                    original_line.qty_returned + prolonged_qty,
                    original_line.product_uom_qty
                )
                original_line.qty_returned = new_returned_qty
                
        # 2. Marquer comme livré dans la nouvelle commande de prolongation
        for extension_line in extension_order.order_line:
            # Marquer tous les articles de la prolongation comme livrés
            extension_line.qty_delivered = extension_line.product_uom_qty
            
        # 3. Confirmer la commande de prolongation si elle n'est pas déjà confirmée
        if extension_order.state in ['draft', 'sent']:
            extension_order.action_confirm()

    def create_extension_order(self):
        """Crée la commande de prolongation et met à jour les quantités livrées/retournées."""
        self.ensure_one()

        # Préparer les valeurs pour la nouvelle commande
        extension_order_vals = self._prepare_extension_order_values()
        extension_order_lines_vals = []

        for wizard_line in self.line_ids.filtered(lambda l: l.selected):
            # Ne pas passer None comme extension_order, car on n'a pas encore créé la commande
            # Stocker les valeurs sans order_id pour l'instant
            line_vals = self._prepare_extension_line_values(self.env['sale.order'], wizard_line)
            extension_order_lines_vals.append((0, 0, line_vals))

        if not extension_order_lines_vals:
            raise UserError(_("Aucun article n'a été sélectionné pour la prolongation."))

        extension_order_vals['order_line'] = extension_order_lines_vals
        
        # Créer la nouvelle commande de prolongation
        extension_order = self.env['sale.order'].create(extension_order_vals)

        # Mettre à jour les quantités livrées/retournées et confirmer la commande
        self._handle_pickings(self.order_id, extension_order)

        # Afficher la nouvelle commande
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': extension_order.id,
            'target': 'current',
        }

class RentalExtensionWizardLine(models.TransientModel):
    _name = 'rental.extension.wizard.line'
    _description = "Lignes de l'assistant de prolongation de location"
    
    wizard_id = fields.Many2one('rental.extension.wizard', string="Assistant", required=True, ondelete='cascade')
    order_line_id = fields.Many2one('sale.order.line', string="Ligne de commande originale", required=True)
    product_id = fields.Many2one('product.product', string="Produit", required=True)
    product_name = fields.Char(string="Description", required=True)
    quantity = fields.Float(string="Quantité", required=True, default=1.0)
    uom_id = fields.Many2one('uom.uom', string="Unité de mesure", required=True)
    selected = fields.Boolean(string="Sélectionné", default=True, 
                              help="Cochez cette case pour inclure ce produit dans la prolongation")
