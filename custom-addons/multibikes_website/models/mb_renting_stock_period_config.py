# -*- coding: utf-8 -*-

from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

class MBRentingStockPeriodConfig(models.Model):
    _name = 'mb.renting.stock.period.config'
    _description = 'Configuration de la période de stock pour la location'
    _rec_name = 'period_id'
    
    period_id = fields.Many2one('mb.renting.period', required=True, ondelete='cascade', string='Période')
    
    # Champ pour lier les produits stockables
    storable_product_ids = fields.Many2many(
        'product.product',
        string='Produits stockables',
        domain=[('is_storable', '=', True)],
        help="Liste des produits stockables associés à cette période"
    )

    storable_product_count = fields.Integer(
        string='Nombre de produits stockables',
        compute='_compute_storable_product_count',
        store=False
    )

    total_stock_by_product = fields.Text(
        string='Détail du stock par produit',
        compute='_compute_total_stock_by_product',
        store=False,
        help="Détail des quantités disponibles par produit"
    )

    stock_available_for_period = fields.Integer(
        string='Stock disponible pour la période',
        help="Stock que vous souhaitez allouer pour cette période",
        default=0
    )

    product_codes = fields.Char(
        string="Références produits", 
        compute="_compute_product_codes", 
        store=False
    )

    @api.depends('storable_product_ids')
    def _compute_product_codes(self):
        for record in self:
            codes = []
            for product in record.storable_product_ids:
                codes.append(product.default_code or product.product_tmpl_id.default_code)
            record.product_codes = ', '.join(filter(None, codes))
    
    @api.depends('storable_product_ids')
    def _compute_storable_product_count(self):
        """Calcule le nombre de produits stockables liés"""
        for record in self:
            record.storable_product_count = len(record.storable_product_ids)

    @api.depends('storable_product_ids')
    def _compute_total_stock_by_product(self):
        """
        Calcule le stock disponible pour chaque produit à travers tous les entrepôts
        et génère un rapport textuel
        """
        _logger.info("Calcul du stock par produit - DÉBUT")
        
        for record in self:
            _logger.info(f"Calcul pour l'enregistrement {record.id}, période {record.period_id.name if record.period_id else 'Non définie'}")
            stock_details_text = []
            
            if record.storable_product_ids:
                # Pour chaque produit, calculer la quantité disponible globalement
                for product in record.storable_product_ids:
                    # Utilisation de qty_available sans contexte pour obtenir le stock total
                    total_qty = product.qty_available
                    _logger.info(f"Produit {product.name} (ID: {product.id}): quantité totale = {total_qty}")
                    
                    # Ajouter ligne de détail pour ce produit
                    stock_details_text.append(f"Produit: {product.name} (Réf: {product.default_code or 'N/A'})")
                    stock_details_text.append(f"Quantité totale disponible: {total_qty}")
                    stock_details_text.append("")
                
                record.total_stock_by_product = "\n".join(stock_details_text) if stock_details_text else "Aucun stock disponible"
            else:
                record.total_stock_by_product = "Aucun produit stockable sélectionné"
            
            _logger.info(f"Texte généré: {record.total_stock_by_product[:100]}...")
        
        _logger.info("Calcul du stock par produit - FIN")

    # Pour forcer le recalcul à chaque chargement de la vue
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Surcharge pour forcer le recalcul des données de stock"""
        res = super(MBRentingStockPeriodConfig, self).search_read(domain, fields, offset, limit, order)
        
        # Si le résultat contient notre champ calculé, recalculer les valeurs
        if fields and 'total_stock_by_product' in fields:
            records = self.browse([r['id'] for r in res])
            records._compute_total_stock_by_product()
            
            # Mettre à jour les résultats avec les nouvelles valeurs calculées
            for i, record in enumerate(records):
                res[i]['total_stock_by_product'] = record.total_stock_by_product
                
        return res
    
    def _needs_transfer(self):
        """Vérifie si ce produit nécessite un transfert à la transition de période"""
        # Stock disponible à la date de début de cette période
        stock_at_period_start = self._get_stock_at_date(self.period_id.start_date)
        desired_stock = self.stock_available_for_period
        return stock_at_period_start != desired_stock

    def _get_stock_at_date(self, target_date):
        """Calcule le stock disponible à une date donnée"""
        if not self.storable_product_ids:
            return 0
        
        # Utiliser l'API Odoo pour calculer le stock à une date donnée
        product = self.storable_product_ids
        stock_at_date = product.with_context(to_date=target_date).qty_available
        return stock_at_date

    def _get_transfer_direction_and_quantity(self):
        """Calcule la direction et quantité du transfert pour la transition"""
        stock_at_period_start = self._get_stock_at_date(self.period_id.start_date)
        desired_stock = self.stock_available_for_period
        difference = stock_at_period_start - desired_stock
        
        if difference > 0:
            # Trop de stock prévu → vers hivernage
            return 'to_winter', difference
        else:
            # Pas assez de stock prévu → depuis hivernage
            return 'from_winter', abs(difference)

    def _create_transfer(self):
        """Crée un transfert programmé pour la date de début de période"""
        if not self.storable_product_ids:
            return None
        
        direction, quantity = self._get_transfer_direction_and_quantity()
        
        if quantity == 0:
            return None
        
        main_warehouse = self.env['stock.warehouse'].get_main_rental_warehouse()
        winter_warehouse = self.env['stock.warehouse'].get_winter_storage_warehouse()
        
        if direction == 'to_winter':
            source_location = main_warehouse.lot_stock_id
            dest_location = winter_warehouse.lot_stock_id
            transfer_type = "vers hivernage"
        else:
            source_location = winter_warehouse.lot_stock_id
            dest_location = main_warehouse.lot_stock_id
            transfer_type = "depuis hivernage"
        
        # Créer le picking programmé pour la date de début de période
        picking_vals = {
            'picking_type_id': main_warehouse.int_type_id.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'scheduled_date': self.period_id.start_date,  # 🎯 DATE DE TRANSITION !
            'origin': f"Transition auto {self.period_id.name} - {transfer_type}",
            'move_ids': [(0, 0, {
                'name': f"Transition {self.storable_product_ids.name}",
                'product_id': self.storable_product_ids.id,
                'product_uom_qty': quantity,
                'product_uom': self.storable_product_ids.uom_id.id,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
                'date': self.period_id.start_date,  # 🎯 DATE PLANIFIÉE !
            })]
        }
        
        return self.env['stock.picking'].create(picking_vals)

    @api.model
    def execute_period_transitions(self):
        """Méthode à appeler par un cron pour exécuter les transferts programmés"""
        now = fields.Datetime.now()
        today = fields.Date.today()
        
        _logger.info(f"Exécution des transitions de période à {now}")
        
        # Chercher les périodes qui commencent aujourd'hui ET qui n'ont pas encore été traitées
        periods_starting_today = self.env['mb.renting.period'].search([
            ('start_date', '=', today)
        ])
        
        transitions_created = 0
        
        for period in periods_starting_today:
            configs = self.search([('period_id', '=', period.id)])
            
            for config in configs:
                if config._needs_transfer():
                    # Vérifier si un transfert n'existe pas déjà pour cette transition
                    existing_transfer = self.env['stock.picking'].search([
                        ('origin', 'ilike', f'Transition auto {period.name}'),
                        ('product_id', '=', config.storable_product_ids.id)
                    ], limit=1)
                    
                    if not existing_transfer:
                        picking = config._create_transfer()
                        if picking:
                            transitions_created += 1
                            _logger.info(f"Transfert créé: {picking.name}")
        
        _logger.info(f"Transitions de période terminées - {transitions_created} transferts créés")
        return transitions_created
    
    def action_generate_transfers(self):
        """
        Action pour générer automatiquement les transferts pour cette configuration
        
        Returns:
            dict: Action de notification ou redirection
        """
        self.ensure_one()
        
        _logger.info(f"🚀 Génération des transferts pour la période {self.period_id.name}")
        
        if not self.storable_product_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': "Aucun produit sélectionné",
                    'message': "Veuillez d'abord sélectionner des produits stockables.",
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Vérifier si des transferts existent déjà pour cette configuration
        existing_transfers = self.env['stock.picking'].search([
            ('origin', 'ilike', f'Transition auto {self.period_id.name}'),
            ('move_ids.product_id', 'in', self.storable_product_ids.ids)
        ])
        
        if existing_transfers:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': "Transferts déjà existants",
                    'message': f"Des transferts existent déjà pour cette période ({len(existing_transfers)} trouvé(s)). "
                            "Voulez-vous les consulter depuis le menu Inventaire?",
                    'type': 'warning',
                    'sticky': True,
                }
            }
        
        transfers_created = []
        errors = []
        
        # Créer un transfert pour chaque produit
        for product in self.storable_product_ids:
            try:
                # Créer une configuration temporaire pour chaque produit
                temp_config = self.copy({'storable_product_ids': [(6, 0, [product.id])]})
                
                if temp_config._needs_transfer():
                    picking = temp_config._create_transfer()
                    if picking:
                        transfers_created.append(picking)
                        _logger.info(f"✅ Transfert créé pour {product.name}: {picking.name}")
                else:
                    _logger.info(f"ℹ️ Aucun transfert nécessaire pour {product.name}")
                
                # Supprimer la config temporaire
                temp_config.unlink()
                
            except Exception as e:
                error_msg = f"Erreur pour {product.name}: {str(e)}"
                errors.append(error_msg)
                _logger.error(f"❌ {error_msg}")
        
        # Préparer le message de retour
        if transfers_created and not errors:
            message = f"✅ {len(transfers_created)} transfert(s) créé(s) avec succès !\n"
            message += "\n".join([f"• {p.name} ({p.origin})" for p in transfers_created])
            notification_type = 'success'
            title = "Transferts générés"
        elif transfers_created and errors:
            message = f"⚠️ {len(transfers_created)} transfert(s) créé(s), {len(errors)} erreur(s):\n"
            message += "\n".join([f"✅ {p.name}" for p in transfers_created])
            message += "\n" + "\n".join([f"❌ {e}" for e in errors])
            notification_type = 'warning'
            title = "Transferts partiellement générés"
        else:
            message = "❌ Aucun transfert généré.\n"
            message += "\n".join([f"• {e}" for e in errors]) if errors else "Vérifiez la configuration."
            notification_type = 'danger'
            title = "Échec de génération"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': notification_type,
                'sticky': True,
            }
        }
