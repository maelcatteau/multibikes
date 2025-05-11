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


class RentalExtensionWizard(models.TransientModel):
    """
    Assistant de prolongation de location
    ------------------------------------
    Cet assistant permet de créer une nouvelle commande de location pour prolonger
    une location existante. Il permet de sélectionner les articles à prolonger,
    de définir la période de prolongation et gère automatiquement les quantités
    livrées et retournées.
    """
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
        """
        Valide les dates de prolongation
        -------------------------------
        - Vérifie que la date de fin est postérieure à la date de début
        - Vérifie que la date de début n'est pas dans le passé
        """
        if self.end_date and self.start_date and self.end_date <= self.start_date:
            _logger.warning(
                "Tentative de prolongation avec date de fin (%s) <= date de début (%s)",
                self.end_date, self.start_date
            )
            raise UserError(_("La date de fin de prolongation doit être postérieure à la date de début."))
        
        # Vérifier que la date de début n'est pas dans le passé
        now = fields.Datetime.now()
        if self.start_date and self.start_date < now:
            _logger.warning(
                "Tentative de prolongation avec date de début (%s) dans le passé (maintenant: %s)",
                self.start_date, now
            )
            raise UserError(_("La date de début de prolongation ne peut pas être dans le passé."))
    
    def _prepare_extension_order_values(self):
        """
        Prépare les valeurs pour la création de la commande de prolongation
        -----------------------------------------------------------------
        Copie les informations pertinentes de la commande d'origine et définit
        les nouvelles dates de location pour la prolongation.
        
        Returns:
            dict: Valeurs pour la création de la commande de prolongation
        """
        original_order = self.order_id
        
        # Durée totale de location (original + prolongation)
        original_duration_days = (original_order.rental_return_date - original_order.rental_start_date).days
        extension_duration_days = (self.end_date - self.start_date).days
        total_duration_days = original_duration_days + extension_duration_days
        
        _logger.info(
            "Préparation de la prolongation pour la commande %s: durée originale=%d jours, "
            "prolongation=%d jours, durée totale=%d jours",
            original_order.name, original_duration_days, extension_duration_days, total_duration_days
        )
        
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
        """
        Prépare les valeurs pour les lignes de la commande de prolongation
        ----------------------------------------------------------------
        Définit les informations de produit, quantité, prix, etc. pour chaque
        ligne de la commande de prolongation.
        
        Args:
            extension_order: La commande de prolongation (peut être vide lors de la préparation)
            wizard_line: La ligne du wizard contenant les informations de l'article à prolonger
            
        Returns:
            dict: Valeurs pour la création de la ligne de commande
        """
        original_line = wizard_line.order_line_id
        product = original_line.product_id
        
        # Calcul de la durée en jours
        start_date = self.start_date
        end_date = self.end_date
        duration_days = (end_date - start_date).days
        
        # Récupérer la catégorie du produit pour appliquer la bonne stratégie de tarification
        category = product.categ_id
        
        # Calcul du prix selon la catégorie de produit
        price_unit = self._calculate_extension_price(product, original_line, duration_days)
        
        _logger.info(
            "Préparation ligne de prolongation: produit=%s, quantité=%s, prix unitaire=%s, "
            "début=%s, fin=%s",
            product.name, wizard_line.quantity, price_unit, 
            start_date.strftime('%d/%m/%Y %H:%M'), end_date.strftime('%d/%m/%Y %H:%M')
        )
        
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
        --------------------------------------------------------------
        Détermine le prix unitaire à appliquer pour la prolongation en fonction
        de la catégorie du produit et de la durée totale de location.
        
        Args:
            product: Le produit à prolonger
            original_line: La ligne de commande originale
            duration_days: La durée de la prolongation en jours
            
        Returns:
            float: Le prix unitaire à appliquer pour la prolongation
        """
        original_order = self.order_id
        original_duration_days = (original_order.rental_return_date - original_order.rental_start_date).days
        total_duration_days = original_duration_days + duration_days
        
        # Récupérer la catégorie du produit
        category = product.categ_id
        
        # Par défaut, on utilise le prix de la ligne originale
        default_price = original_line.price_unit
        
        # Logique de tarification basée sur la catégorie de produit
        # Approche plus sécurisée avec identification par ID ou propriétés plutôt que par nom
        try:
            # Vérifier si la catégorie est une catégorie de vélos (à adapter selon votre structure)
            is_bike_category = category.id in self.env['product.category'].search([
                ('name', 'ilike', 'vélo')
            ]).ids
            
            # Vérifier si la catégorie est une catégorie d'accessoires
            is_accessory_category = category.id in self.env['product.category'].search([
                ('name', 'ilike', 'accessoire')
            ]).ids
            
            # Appliquer la logique de tarification
            if is_bike_category:
                if total_duration_days <= 5:
                    _logger.debug("Prix de prolongation pour vélo: utilisation du prix original %s (durée totale <= 5 jours)", default_price)
                    return default_price
                else:
                    _logger.debug("Prix de prolongation pour vélo: utilisation du prix spécial 4.5€ (durée totale > 5 jours)")
                    return 4.5  # 4.5€ par jour pour les jours de prolongation
            elif is_accessory_category:
                if total_duration_days <= 3:
                    _logger.debug("Prix de prolongation pour accessoire: utilisation du prix original %s (durée totale <= 3 jours)", default_price)
                    return default_price
                else:
                    _logger.debug("Prix de prolongation pour accessoire: utilisation du prix spécial 2.5€ (durée totale > 3 jours)")
                    return 2.5  # 2.5€ par jour pour les jours de prolongation
            else:
                # Prix par défaut pour les autres catégories
                _logger.debug("Prix de prolongation pour catégorie %s: utilisation du prix par défaut %s", category.name, default_price)
                return default_price
                
        except Exception as e:
            # En cas d'erreur, utiliser le prix par défaut et logger l'erreur
            _logger.error("Erreur lors du calcul du prix de prolongation: %s", str(e))
            return default_price
    
    def _handle_pickings(self, original_order, extension_order):
        """
        Met à jour les quantités retournées et livrées des lignes de commande
        -------------------------------------------------------------------
        Cette méthode gère la logique métier principale de la prolongation:
        1. Marque les articles sélectionnés de la commande originale comme retournés
        2. Marque les articles de la nouvelle commande comme livrés
        3. Confirme la nouvelle commande de prolongation
        
        Args:
            original_order: La commande de location d'origine
            extension_order: La nouvelle commande de prolongation
        """
        _logger.info(
            "Traitement des quantités pour la prolongation: commande originale=%s, nouvelle commande=%s",
            original_order.name, extension_order.name
        )
        
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
                
                _logger.info(
                    "Mise à jour quantité retournée: produit=%s, ligne=%s, ancienne valeur=%s, nouvelle valeur=%s",
                    original_line.product_id.name, original_line.id, 
                    original_line.qty_returned, new_returned_qty
                )
                
                original_line.qty_returned = new_returned_qty
                
        # 2. Marquer comme livré dans la nouvelle commande de prolongation
        for extension_line in extension_order.order_line:
            # Marquer tous les articles de la prolongation comme livrés
            _logger.info(
                "Mise à jour quantité livrée: produit=%s, ligne=%s, valeur=%s",
                extension_line.product_id.name, extension_line.id, extension_line.product_uom_qty
            )
            extension_line.qty_delivered = extension_line.product_uom_qty
            
        # 3. Confirmer la commande de prolongation si elle n'est pas déjà confirmée
        if extension_order.state in ['draft', 'sent']:
            _logger.info("Confirmation de la commande de prolongation %s", extension_order.name)
            extension_order.action_confirm()

    def create_extension_order(self):
        """
        Crée la commande de prolongation et met à jour les quantités livrées/retournées
        ----------------------------------------------------------------------------
        Cette méthode principale de l'assistant:
        1. Valide les données (quantités, chevauchements)
        2. Crée une nouvelle commande de location pour la prolongation
        3. Met à jour les quantités livrées/retournées
        4. Confirme la nouvelle commande
        
        Returns:
            dict: Action pour afficher la nouvelle commande de prolongation créée
            
        Raises:
            UserError: Si aucun article n'est sélectionné ou si les validations échouent
        """
        self.ensure_one()
        
        _logger.info(
            "Création d'une prolongation pour la commande %s du %s au %s",
            self.order_id.name, self.start_date, self.end_date
        )

        # Validation supplémentaire des quantités
        for wizard_line in self.line_ids.filtered(lambda l: l.selected):
            available_qty = wizard_line.order_line_id.qty_delivered - wizard_line.order_line_id.qty_returned
            if wizard_line.quantity > available_qty:
                _logger.warning(
                    "Tentative de prolongation avec quantité excessive: produit=%s, demandé=%s, disponible=%s",
                    wizard_line.product_id.name, wizard_line.quantity, available_qty
                )
                raise UserError(_(
                    "Impossible de prolonger %s unités de l'article %s. "
                    "Seulement %s unités sont disponibles pour prolongation "
                    "(différence entre quantité livrée et retournée)."
                ) % (wizard_line.quantity, wizard_line.product_id.name, available_qty))
        
        # Vérifier s'il y a des chevauchements avec d'autres prolongations
        self._check_extension_overlaps()
        
        # Préparer les valeurs pour la nouvelle commande
        extension_order_vals = self._prepare_extension_order_values()
        extension_order_lines_vals = []

        for wizard_line in self.line_ids.filtered(lambda l: l.selected):
            # Ne pas passer None comme extension_order, car on n'a pas encore créé la commande
            # Stocker les valeurs sans order_id pour l'instant
            line_vals = self._prepare_extension_line_values(self.env['sale.order'], wizard_line)
            extension_order_lines_vals.append((0, 0, line_vals))

        if not extension_order_lines_vals:
            _logger.warning("Tentative de prolongation sans sélection d'articles")
            raise UserError(_("Aucun article n'a été sélectionné pour la prolongation. Veuillez sélectionner au moins un article."))

        extension_order_vals['order_line'] = extension_order_lines_vals
        
        # Créer la nouvelle commande de prolongation
        _logger.info("Création de la commande de prolongation")
        extension_order = self.env['sale.order'].create(extension_order_vals)
        _logger.info("Commande de prolongation créée: %s", extension_order.name)

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

    def _check_extension_overlaps(self):
        """
        Vérifie s'il y a des chevauchements avec d'autres prolongations pour les mêmes articles
        ------------------------------------------------------------------------------------
        Cette méthode évite les conflits de prolongation en vérifiant si les articles
        sélectionnés sont déjà prolongés pour la même période dans d'autres commandes.
        
        Raises:
            UserError: Si un chevauchement est détecté
        """
        original_order = self.order_id
        
        _logger.debug("Vérification des chevauchements de prolongation pour la commande %s", original_order.name)
        
        # Pour chaque ligne sélectionnée, vérifier les chevauchements potentiels
        for wizard_line in self.line_ids.filtered(lambda l: l.selected):
            product = wizard_line.product_id
            
            _logger.debug("Vérification des chevauchements pour le produit %s", product.name)
            
            # Chercher toutes les prolongations existantes pour la commande d'origine
            existing_extensions = self.env['sale.order'].search([
                ('original_rental_id', '=', original_order.id),
                ('state', 'not in', ['cancel', 'draft'])
            ])
            
            # Ajouter aussi les prolongations des prolongations (si possible)
            child_extensions = self.env['sale.order']
            for ext in existing_extensions:
                child_extensions |= self.env['sale.order'].search([
                    ('original_rental_id', '=', ext.id),
                    ('state', 'not in', ['cancel', 'draft'])
                ])
            
            all_extensions = existing_extensions | child_extensions
            
            if all_extensions:
                _logger.debug(
                    "Prolongations existantes trouvées pour la commande %s: %s",
                    original_order.name, ", ".join(all_extensions.mapped('name'))
                )
            
            # Pour chaque extension existante, vérifier si le produit est présent
            # et si les dates se chevauchent
            for extension in all_extensions:
                extension_lines = extension.order_line.filtered(
                    lambda l: l.product_id.id == product.id and l.is_rental
                )
                
                if not extension_lines:
                    continue
                    
                for ext_line in extension_lines:
                    # Vérifier le chevauchement de dates
                    if (extension.rental_start_date <= self.end_date and 
                        extension.rental_return_date >= self.start_date):
                        
                        _logger.warning(
                            "Chevauchement détecté pour le produit %s entre %s-%s et la prolongation %s (%s-%s)",
                            product.name,
                            self.start_date, self.end_date,
                            extension.name, extension.rental_start_date, extension.rental_return_date
                        )
                        
                        raise UserError(_(
                            "Chevauchement détecté! L'article %s est déjà prolongé dans la commande %s "
                            "pour la période du %s au %s."
                        ) % (
                            product.name,
                            extension.name,
                            extension.rental_start_date.strftime('%d/%m/%Y %H:%M'),
                            extension.rental_return_date.strftime('%d/%m/%Y %H:%M')
                        ))

class RentalExtensionWizardLine(models.TransientModel):
    """
    Lignes de l'assistant de prolongation de location
    -----------------------------------------------
    Cette classe représente les lignes du wizard de prolongation, permettant
    de sélectionner les articles à prolonger et leurs quantités.
    """
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
    available_qty = fields.Float(string="Quantité disponible", compute='_compute_available_qty', 
                               help="Quantité disponible pour prolongation (livrée mais pas encore retournée)")
    
    @api.depends('order_line_id')
    def _compute_available_qty(self):
        """
        Calcule la quantité disponible pour prolongation
        ----------------------------------------------
        La quantité disponible est la différence entre la quantité livrée
        et la quantité déjà retournée pour chaque ligne de commande.
        """
        for line in self:
            if line.order_line_id:
                line.available_qty = line.order_line_id.qty_delivered - line.order_line_id.qty_returned
                _logger.debug(
                    "Calcul quantité disponible: produit=%s, ligne=%s, livrée=%s, retournée=%s, disponible=%s",
                    line.product_id.name, line.order_line_id.id,
                    line.order_line_id.qty_delivered, line.order_line_id.qty_returned, line.available_qty
                )
            else:
                line.available_qty = 0.0
    
    @api.onchange('quantity')
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
            if line.quantity > line.available_qty:
                _logger.warning(
                    "Tentative de prolongation avec quantité excessive: produit=%s, demandé=%s, disponible=%s",
                    line.product_id.name, line.quantity, line.available_qty
                )
                raise UserError(_(
                    "Vous ne pouvez pas prolonger plus de %s unités pour l'article %s. "
                    "Cette quantité correspond aux articles actuellement en location (non retournés)."
                ) % (line.available_qty, line.product_id.name))
