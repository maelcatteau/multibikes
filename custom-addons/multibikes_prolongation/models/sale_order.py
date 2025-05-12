# -*- coding: utf-8 -*-
"""
Module de prolongation de location pour Multibikes - Modèle Sale Order
--------------------------------------------------------------------
Extension du modèle sale.order pour ajouter les fonctionnalités de prolongation
de location. Ce module permet de lier les commandes de prolongation aux commandes
de location d'origine et de suivre les prolongations.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    """
    Extension du modèle Sale Order pour la prolongation de location
    -------------------------------------------------------------
    Ajoute les champs et méthodes nécessaires pour gérer les prolongations
    de location et les liens entre commandes originales et prolongations.
    """
    _inherit = 'sale.order'

    mb_is_rental_extension = fields.Boolean(
        string="Est une prolongation",
        default=False,
        help="Indique si cette commande est une prolongation d'une location existante"
    )
    mb_original_rental_id = fields.Many2one(
        'sale.order',
        string="Location d'origine",
        help="La commande de location d'origine dont celle-ci est une prolongation"
    )
    mb_extension_count = fields.Integer(
        string="Nombre de prolongations",
        compute='_compute_mb_extension_count',
        help="Nombre de prolongations liées à cette location"
    )
    mb_rental_extensions_ids = fields.One2many(
        'sale.order',
        'mb_original_rental_id',
        string="Prolongations de location",
        help="Liste des prolongations liées à cette location"
    )
    mb_has_rentable_lines = fields.Boolean(
        string="A des articles prolongeables",
        compute='_compute_mb_has_rentable_lines',
        help="Indique s'il reste des articles qui peuvent être prolongés (livrés mais pas encore retournés)"
    )
    
    @api.depends('order_line.qty_delivered', 'order_line.qty_returned')
    def _compute_mb_has_rentable_lines(self):
        """
        Vérifie s'il reste des articles à prolonger (livrés mais pas encore totalement retournés)
        --------------------------------------------------------------------------------------
        Ce champ calculé est utilisé pour déterminer si le bouton de prolongation
        doit être affiché ou non dans l'interface.
    
        Optimisation: Utilise une requête SQL directe pour éviter de charger tous les objets
        en mémoire, ce qui améliore significativement les performances pour les grandes commandes.
        """
        # Initialiser toutes les commandes à False dès le début
        for order in self:
            order.mb_has_rentable_lines = False
            
        if not self.ids:
            return
        
        _logger.debug("Calcul des commandes avec articles prolongeables pour %d commandes", len(self))
        
        # Exécuter une requête SQL directe pour identifier les commandes avec des articles prolongeables
        self.env.cr.execute("""
            SELECT so.id
            FROM sale_order so
            JOIN sale_order_line sol ON sol.order_id = so.id
            WHERE so.id IN %s
            AND sol.is_rental = TRUE
            AND sol.qty_delivered > sol.qty_returned
            GROUP BY so.id
        """, (tuple(self.ids),))
        
        # Récupérer les IDs des commandes avec des articles prolongeables
        order_ids_with_rentable_lines = [row[0] for row in self.env.cr.fetchall()]
        
        if order_ids_with_rentable_lines:
            _logger.debug(
                "Commandes avec articles prolongeables trouvées: %s", 
                ", ".join(map(str, order_ids_with_rentable_lines))
            )
            
            # Mettre à jour uniquement les commandes qui ont des articles prolongeables
            for order in self:
                if order.id in order_ids_with_rentable_lines:
                    order.mb_has_rentable_lines = True

    @api.depends('mb_rental_extensions_ids')
    def _compute_mb_extension_count(self):
        """
        Calcule le nombre de prolongations liées à cette location
        -------------------------------------------------------
        Ce champ est utilisé pour l'affichage dans l'interface et pour
        déterminer si des prolongations existent pour cette commande.
        """
        for order in self:
            count = len(order.mb_rental_extensions_ids)
            order.mb_extension_count = count
            if count > 0:
                _logger.debug(
                    "Commande %s: %d prolongation(s) trouvée(s)",
                    order.name, count
                )
    
    def action_extend_rental(self):
        """
        Ouvre un assistant pour prolonger la location
        -------------------------------------------
        Cette méthode est appelée lorsque l'utilisateur clique sur le bouton
        "Prolonger la location" dans l'interface. Elle vérifie que la commande
        est bien une location confirmée, puis ouvre l'assistant de prolongation.
        
        Returns:
            dict: Action pour ouvrir l'assistant de prolongation
            
        Raises:
            UserError: Si la commande n'est pas une location ou n'est pas confirmée
        """
        self.ensure_one()
        
        # Vérifier que c'est bien une location
        if not self.is_rental_order:
            _logger.warning("Tentative de prolongation sur une commande non-location: %s", self.name)
            raise UserError(_("Cette commande n'est pas une location. Seules les commandes de location peuvent être prolongées."))
        
        # Vérifier que la location est confirmée
        if self.state not in ['sale', 'done']:
            _logger.warning(
                "Tentative de prolongation sur une commande non-confirmée: %s (état: %s)",
                self.name, self.state
            )
            raise UserError(_(
                "La location doit être confirmée avant de pouvoir être prolongée. "
                "État actuel: %s"
            ) % (dict(self._fields['state']._description_selection(self.env)).get(self.state)))
        
        _logger.info("Ouverture de l'assistant de prolongation pour la commande %s", self.name)
        
        # Préparer les lignes de l'assistant
        wizard_line_vals = []
        for line in self.order_line:
            # Ne créer une ligne que si c'est un article de location
            if not line.is_rental:
                continue
                
            # Ne créer une ligne que s'il reste des articles à prolonger
            available_qty = line.qty_delivered - line.qty_returned
            if available_qty <= 0:
                continue
                
            # Créer une ligne pour chaque produit de la commande
            wizard_line_vals.append((0, 0, {
                'mb_order_line_id': line.id,
                'mb_product_id': line.product_id.id,
                'mb_product_name': line.name,
                'mb_quantity': available_qty,  # Par défaut, proposer la quantité disponible
                'mb_uom_id': line.product_uom.id,
                'mb_selected': True,  # Par défaut, tous les produits sont sélectionnés
            }))
        
        if not wizard_line_vals:
            _logger.warning("Aucun article disponible pour prolongation dans la commande %s", self.name)
            raise UserError(_(
                "Aucun article n'est disponible pour prolongation. "
                "Tous les articles ont déjà été retournés ou aucun n'a été livré."
            ))
        
        # Créer et ouvrir l'assistant
        context = dict(
            self.env.context,
            default_mb_order_id=self.id,
            default_mb_start_date=self.rental_return_date,  # Date de fin actuelle comme date de début de prolongation
        )
        
        # Créer le wizard
        wizard = self.env['rental.extension.wizard'].create({
            'mb_order_id': self.id,
            'mb_start_date': self.rental_return_date,
            'mb_end_date': self.rental_return_date + timedelta(days=1),  # Par défaut, prolongation d'un jour
            'mb_line_ids': wizard_line_vals,
        })
        
        _logger.info("Assistant de prolongation créé pour la commande %s: wizard_id=%d", self.name, wizard.id)
        
        return {
            'name': _('Prolonger la location'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'rental.extension.wizard',
            'res_id': wizard.id,
            'view_id': self.env.ref('multibikes_prolongation.view_rental_extension_wizard_form').id,
            'target': 'new',
            'context': context,
        }
    
    def action_view_extensions(self):
        """
        Affiche les prolongations liées à cette location
        ----------------------------------------------
        Cette méthode est appelée lorsque l'utilisateur clique sur le lien
        pour voir les prolongations dans l'onglet "Prolongations".
        
        Returns:
            dict: Action pour afficher la liste des prolongations
        """
        self.ensure_one()
        
        _logger.debug("Affichage des prolongations pour la commande %s", self.name)
        
        return {
            'name': _('Prolongations'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'sale.order',
            'domain': [('mb_original_rental_id', '=', self.id)],
            'context': {'create': False}
        }


