# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo.tests import tagged
from odoo.exceptions import ValidationError
from .common import MultibikesWebsiteTestCommon

@tagged('post_install', '-at_install')
class TestMBRentingPeriod(MultibikesWebsiteTestCommon):
    """Tests pour le modèle mb.renting.period"""
    
    def test_find_period_for_date(self):
        """Test de la méthode find_period_for_date"""
        # Date dans la période
        period = self.env['mb.renting.period'].find_period_for_date(self.today + timedelta(days=5), self.test_company.id)
        self.assertEqual(period.id, self.test_period.id)
        
        # Date hors période
        period = self.env['mb.renting.period'].find_period_for_date(self.next_month + timedelta(days=10), self.test_company.id)
        self.assertFalse(period)
        
        # Test avec la société par défaut
        # Remarque: ce test suppose que le self.test_period a été créé avec la société actuelle
        period = self.env['mb.renting.period'].find_period_for_date(self.today + timedelta(days=5))
        self.assertNotEqual(period.id, self.test_period.id)  # Ne devrait pas trouver notre période de test qui a une compagnie spécifique
    
    def test_compute_total_storable_products(self):
        """Test du calcul du nombre total de produits stockables"""
        self.test_period._compute_total_storable_products()
        # Vérifier que les 2 produits stockables créés sont comptabilisés
        self.assertEqual(self.test_period.total_storable_products, 2)
    
    def test_compute_products_to_configure(self):
        """Test du calcul des produits restants à configurer"""
        self.test_period._compute_products_to_configure()
        
        # Au départ, 1 produit est déjà configuré (storable_product)
        self.assertEqual(self.test_period.remaining_products_to_configure, 1)  # storable_product2 reste à configurer
        
        # Ajouter le deuxième produit à la configuration
        self.stock_period_config.write({
            'storable_product_ids': [(6, 0, [self.storable_product.id, self.storable_product2.id])]
        })
        
        # Recalculer
        self.test_period._compute_products_to_configure()
        
        # Tous les produits sont maintenant configurés
        self.assertEqual(self.test_period.remaining_products_to_configure, 0)
    
    def test_sql_constraints(self):
        """Test des contraintes SQL"""
        # Test de la contrainte date_check
        with self.assertRaises(ValidationError):
            self.env['mb.renting.period'].create({
                'name': 'Invalid Period',
                'company_id': self.test_company.id,
                'start_date': self.next_month,  # Date de début après date de fin
                'end_date': self.today,
            })
        
        # Test de la contrainte company_dates_unique
        with self.assertRaises(Exception):  # ValidationError ou IntegrityError selon l'implémentation
            self.env['mb.renting.period'].create({
                'name': 'Duplicate Period',
                'company_id': self.test_company.id,
                'start_date': self.today,  # Mêmes dates que test_period
                'end_date': self.next_month,
            })
