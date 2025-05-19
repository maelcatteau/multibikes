# -*- coding: utf-8 -*-
from odoo.tests import tagged
from .common import MultibikesWebsiteTestCommon

@tagged('post_install', '-at_install')
class TestMBRentingStockPeriodConfig(MultibikesWebsiteTestCommon):
    """Tests pour le modèle mb.renting.stock.period.config"""
    
    def test_compute_storable_product_count(self):
        """Test du calcul du nombre de produits stockables"""
        # Vérifier le compte initial
        self.stock_period_config._compute_storable_product_count()
        self.assertEqual(self.stock_period_config.storable_product_count, 1)
        
        # Ajouter un deuxième produit
        self.stock_period_config.write({
            'storable_product_ids': [(6, 0, [self.storable_product.id, self.storable_product2.id])]
        })
        
        # Vérifier le nouveau compte
        self.stock_period_config._compute_storable_product_count()
        self.assertEqual(self.stock_period_config.storable_product_count, 2)
    
    def test_compute_product_codes(self):
        """Test du calcul des codes produits"""
        # Vérifier les codes initiaux
        self.stock_period_config._compute_product_codes()
        self.assertEqual(self.stock_period_config.product_codes, 'VST001')
        
        # Ajouter un deuxième produit
        self.stock_period_config.write({
            'storable_product_ids': [(6, 0, [self.storable_product.id, self.storable_product2.id])]
        })
        
        # Vérifier les nouveaux codes
        self.stock_period_config._compute_product_codes()
        self.assertIn('VST001', self.stock_period_config.product_codes)
        self.assertIn('VST002', self.stock_period_config.product_codes)
        
    def test_compute_total_stock_by_product(self):
        """Test du calcul du stock total par produit"""
        # Configurer des quantités de stock initiales
        self.env['stock.quant'].create({
            'product_id': self.storable_product.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 5,
        })
        
        # Calculer le stock
        self.stock_period_config._compute_total_stock_by_product()
        
        # Vérifier que le texte généré contient les informations attendues
        self.assertIn("Produit: Vélo Stockable Test", self.stock_period_config.total_stock_by_product)
        self.assertIn("Réf: VST001", self.stock_period_config.total_stock_by_product)
        self.assertIn("Quantité totale disponible: 5", self.stock_period_config.total_stock_by_product)
        
        # Ajouter plus de stock et vérifier la mise à jour
        self.env['stock.quant'].create({
            'product_id': self.storable_product.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 3,
        })
        
        # Recalculer
        self.stock_period_config._compute_total_stock_by_product()
        self.assertIn("Quantité totale disponible: 8", self.stock_period_config.total_stock_by_product)
    
    def test_search_read_recalculation(self):
        """Test que search_read force le recalcul des données de stock"""
        # Configuration initiale
        self.env['stock.quant'].create({
            'product_id': self.storable_product.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 5,
        })
        
        # Effectuer un search_read incluant notre champ calculé
        result = self.env['mb.renting.stock.period.config'].search_read(
            [('id', '=', self.stock_period_config.id)],
            ['id', 'total_stock_by_product']
        )
        
        # Vérifier que le résultat contient les informations à jour
        self.assertEqual(len(result), 1)
        self.assertIn("Quantité totale disponible: 5", result[0]['total_stock_by_product'])
        
        # Ajouter plus de stock
        self.env['stock.quant'].create({
            'product_id': self.storable_product.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 3,
        })
        
        # Effectuer un nouveau search_read
        result = self.env['mb.renting.stock.period.config'].search_read(
            [('id', '=', self.stock_period_config.id)],
            ['id', 'total_stock_by_product']
        )
        
        # Vérifier que le résultat contient les informations mises à jour
        self.assertIn("Quantité totale disponible: 8", result[0]['total_stock_by_product'])
