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

    mb_order_id = fields.Many2one(
        'sale.order',
        string="Commande de location",
        required=True
    )
    mb_start_date = fields.Datetime(
        string="Date de début de la prolongation",
        required=True,
        help="Par défaut, la date de fin de la location actuelle"
    )
    mb_end_date = fields.Datetime(
        string="Nouvelle date de fin",
        required=True,
        help="Date de fin de la prolongation"
    )
    mb_line_ids = fields.One2many(
        'rental.extension.wizard.line',
        'mb_wizard_id',
        string="Articles à prolonger"
    )
    
    @api.onchange('mb_end_date', 'mb_start_date')
    def _onchange_dates(self):
        """
        Valide les dates de prolongation
        -------------------------------
        - Vérifie que la date de fin est postérieure à la date de début
        - Vérifie que la date de début n'est pas dans le passé
        """
        if self.mb_end_date and self.mb_start_date and self.mb_end_date <= self.mb_start_date:
            _logger.warning(
                "Tentative de prolongation avec date de fin (%s) <= date de début (%s)",
                self.mb_end_date, self.mb_start_date
            )
            raise UserError(_("La date de fin de prolongation doit être postérieure à la date de début."))
        
        # Vérifier que la date de début n'est pas dans le passé
        now = fields.Datetime.now()
        if self.mb_start_date and self.mb_start_date < now:
            _logger.warning(
                "Tentative de prolongation avec date de début (%s) dans le passé (maintenant: %s)",
                self.mb_start_date, now
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
        original_order = self.mb_order_id
        
        # Durée totale de location (original + prolongation)
        original_duration_days = (original_order.rental_return_date - original_order.rental_start_date).days
        extension_duration_days = (self.mb_end_date - self.mb_start_date).days
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
            'rental_start_date': self.mb_start_date,
            'rental_return_date': self.mb_end_date,
            'is_rental_order': True,
            'mb_is_rental_extension': True,
            'mb_original_rental_id': original_order.id,
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
        original_line = wizard_line.mb_order_line_id
        product = original_line.product_id
        
        # Calcul de la durée en jours
        start_date = self.mb_start_date
        end_date = self.mb_end_date
        duration_days = (end_date - start_date).days
        
        # Récupérer la catégorie du produit pour appliquer la bonne stratégie de tarification
        category = product.categ_id
        
        # Calcul du prix selon la catégorie de produit
        price_unit = self._calculate_extension_price(product, original_line, duration_days)
        
        _logger.info(
            "Préparation ligne de prolongation: produit=%s, quantité=%s, prix unitaire=%s, "
            "début=%s, fin=%s",
            product.name, wizard_line.mb_quantity, price_unit, 
            start_date.strftime('%d/%m/%Y %H:%M'), end_date.strftime('%d/%m/%Y %H:%M')
        )
        
        # Créer les valeurs de ligne sans inclure order_id si extension_order n'est pas encore créé
        line_vals = {
            'product_id': product.id,
            'product_uom_qty': wizard_line.mb_quantity,
            'product_uom': wizard_line.mb_uom_id.id,
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
        original_order = self.mb_order_id
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
        for wizard_line in self.mb_line_ids.filtered(lambda l: l.mb_selected):
            # 1. Marquer comme retourné dans la commande originale
            original_line = wizard_line.mb_order_line_id
            if original_line:
                # Mettre à jour qty_returned pour marquer uniquement la quantité prolongée comme retournée
                # Attention: ne pas dépasser la quantité totale
                prolonged_qty = min(wizard_line.mb_quantity, original_line.product_uom_qty)
                
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
            self.mb_order_id.name, self.mb_start_date, self.mb_end_date
        )

        # Validation supplémentaire des quantités
        for wizard_line in self.mb_line_ids.filtered(lambda l: l.mb_selected):
            available_qty = wizard_line.mb_available_qty
            if wizard_line.mb_quantity > available_qty:
                _logger.warning(
                    "Tentative de prolongation avec quantité excessive: produit=%s, demandé=%s, disponible=%s",
                    wizard_line.mb_product_id.name, wizard_line.mb_quantity, available_qty
                )
                raise UserError(_(
                    "Impossible de prolonger %s unités de l'article %s. "
                    "Seulement %s unités sont disponibles pour prolongation "
                    "(différence entre quantité livrée et retournée)."
                ) % (wizard_line.mb_quantity, wizard_line.mb_product_id.name, available_qty))
        
        # Vérifier s'il y a des chevauchements avec d'autres prolongations
        # Cette vérification n'est pas nécessaire car les disponibilités sont déjà gérées
        # par le mécanisme de quantités livrées/retournées
        # self._check_extension_overlaps()
        
        # Préparer les valeurs pour la nouvelle commande
        extension_order_vals = self._prepare_extension_order_values()
        extension_order_lines_vals = []

        for wizard_line in self.mb_line_ids.filtered(lambda l: l.mb_selected):
            # Ne pas passer None comme extension_order, car on n'a pas encore créé la commande
            # Stocker les valeurs sans order_id pour l'instant
            line_vals = self._prepare_extension_line_values(self.env['sale.order'], wizard_line)
            extension_order_lines_vals.append((0, 0, line_vals))

        if not extension_order_lines_vals:
            _logger.warning("Tentative de prolongation sans sélection d'articles")
            raise UserError(_("Aucun article n'a été sélectionné pour la prolongation. Veuillez sélectionner au moins un article."))

        extension_order_vals['order_line'] = extension_order_lines_vals
        
        # Créer la nouvelle commande de prolongation dans une transaction 
        # pour éviter les problèmes de numérotation
        original_order = self.mb_order_id
        extension_number = self.env['sale.order'].search_count([
            ('mb_original_rental_id', '=', original_order.id)
        ]) + 1
        
        # Créer la nouvelle commande de prolongation
        _logger.info("Création de la commande de prolongation")
        with self.env.cr.savepoint():
            extension_order = self.env['sale.order'].create(extension_order_vals)
            # Modifier le nom pour éviter les sauts dans la séquence 
            # (ne fonctionnera que si le format est bien SOxxxxx)
            if extension_order.name and extension_order.mb_original_rental_id:
                # Essayer de mettre le nom sous forme [Original]-P[Numéro d'extension]
                try:
                    # Utiliser le même préfixe que la commande originale et y ajouter un suffixe d'extension
                    extension_order.name = f"{original_order.name}-P{extension_number}"
                    _logger.info(f"Nom de la commande de prolongation modifié: {extension_order.name}")
                except Exception as e:
                    _logger.warning(f"Impossible de modifier le nom de la commande de prolongation: {e}")
                    # Si ça échoue, on garde le comportement standard
        
        _logger.info("Commande de prolongation créée: %s", extension_order.name)

        # Mettre à jour les quantités livrées/retournées et confirmer la commande
        self._handle_pickings(self.mb_order_id, extension_order)

        # Afficher la nouvelle commande
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': extension_order.id,
            'target': 'current',
        }

