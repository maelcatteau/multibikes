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
        
        return {
            'order_id': extension_order.id,
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
        """Gère les mouvements de stock pour la prolongation"""
        # Récupérer les pickings originaux
        return_pickings = original_order.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing' and p.state not in ['done', 'cancel'] and 
            p.rental_operation == 'return'
        )
        
        if not return_pickings:
            raise UserError(_("Aucun bon de retour en attente trouvé pour cette location."))
        
        # 1. Modifier la date de retour prévisionnelle pour les pickings de retour existants
        for picking in return_pickings:
            picking.scheduled_date = self.start_date
            # Confirmer si nécessaire
            if picking.state == 'draft':
                picking.action_confirm()
        
        # 2. S'assurer que les pickings de livraison pour la prolongation sont créés
        extension_order.action_confirm()
        
        # 3. Ajuster les dates des nouveaux pickings
        extension_pickings = extension_order.picking_ids
        for picking in extension_pickings:
            if picking.picking_type_code == 'outgoing' and picking.rental_operation == 'pickup':
                picking.scheduled_date = self.start_date
            elif picking.picking_type_code == 'outgoing' and picking.rental_operation == 'return':
                picking.scheduled_date = self.end_date
    
    def action_extend_rental(self):
        """Crée la commande de prolongation de location"""
        self.ensure_one()
        original_order = self.order_id
        
        # Vérifier que c'est une location
        if not original_order.is_rental_order:
            raise UserError(_("Cette commande n'est pas une location."))
        
        # Vérifier qu'au moins une ligne est sélectionnée
        selected_lines = self.line_ids.filtered(lambda l: l.selected)
        if not selected_lines:
            raise UserError(_("Veuillez sélectionner au moins un article à prolonger."))
        
        # Créer la nouvelle commande
        extension_vals = self._prepare_extension_order_values()
        extension_order = self.env['sale.order'].create(extension_vals)
        
        # Créer les lignes de commande pour chaque produit sélectionné
        for wizard_line in selected_lines:
            line_vals = self._prepare_extension_line_values(extension_order, wizard_line)
            self.env['sale.order.line'].create(line_vals)
        
        # Confirmer la nouvelle commande
        extension_order.action_confirm()
        
        # Gérer les mouvements de stock (toujours activé)
        self._handle_pickings(original_order, extension_order)
        
        # Afficher un message de succès
        view_id = self.env.ref('sale.view_order_form').id
        return {
            'name': _('Prolongation de location créée'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'views': [(view_id, 'form')],
            'res_id': extension_order.id,
            'target': 'current',
            'context': {'form_view_initial_mode': 'edit'},
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
