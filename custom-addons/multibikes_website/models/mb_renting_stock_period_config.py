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
