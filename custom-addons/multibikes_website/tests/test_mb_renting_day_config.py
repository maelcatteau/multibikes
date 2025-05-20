# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo.tests import tagged
from .common import MultibikesWebsiteTestCommon
import logging

_logger = logging.getLogger(__name__)

@tagged('post_install', '-at_install')
class TestMBRentingDayConfig(MultibikesWebsiteTestCommon):
    """Tests pour le modèle mb.renting.day.config"""
    
    def test_onchange_is_open(self):
        """Test du comportement quand is_open est changé"""
        # Vérifier l'état initial
        self.assertTrue(self.monday_config.is_open)
        self.assertTrue(self.monday_config.allow_pickup)
        self.assertTrue(self.monday_config.allow_return)
        
        # Simuler l'onchange
        self.monday_config._onchange_is_open()
        
        # Rien ne devrait changer car is_open est True
        self.assertTrue(self.monday_config.allow_pickup)
        self.assertTrue(self.monday_config.allow_return)
        
        # Changer is_open à False
        self.monday_config.is_open = False
        self.monday_config._onchange_is_open()
        
        # Vérifier que les valeurs sont réinitialisées
        self.assertFalse(self.monday_config.allow_pickup)
        self.assertFalse(self.monday_config.allow_return)
        self.assertFalse(self.monday_config.pickup_hour_from)
        self.assertFalse(self.monday_config.pickup_hour_to)
        self.assertFalse(self.monday_config.return_hour_from)
        self.assertFalse(self.monday_config.return_hour_to)
    
    def test_get_config_for_date(self):
        """Test de la méthode get_config_for_date"""
        # Trouver un lundi dans la période de test
        test_date = self.today
        while test_date.weekday() != 0:  # 0 = Lundi
            test_date += timedelta(days=1)
        
        # Obtenir la config pour ce lundi
        config = self.env['mb.renting.day.config'].get_config_for_date(test_date, self.main_company.id)
        
        # Vérifier que c'est bien la config du lundi
        self.assertEqual(config.id, self.monday_config.id)
        
        # Trouver un dimanche
        test_date = self.today
        while test_date.weekday() != 6:  # 6 = Dimanche
            test_date += timedelta(days=1)
        
        # Obtenir la config pour ce dimanche
        config = self.env['mb.renting.day.config'].get_config_for_date(test_date, self.main_company.id)
        
        # Vérifier que c'est bien la config du dimanche
        self.assertEqual(config.id, self.sunday_config.id)
        
        # Test avec une date hors période
        out_of_period_date = self.next_month + timedelta(days=10)
        config = self.env['mb.renting.day.config'].get_config_for_date(out_of_period_date, self.main_company.id)
        
        # Aucune config ne devrait être trouvée
        self.assertFalse(config)
    
    def test_is_pickup_allowed(self):
        """Test de la méthode is_pickup_allowed"""
        # Test avec jour ouvert et heure valide
        self.assertTrue(self.monday_config.is_pickup_allowed(10.0))
        
        # Test avec jour ouvert et heure invalide
        self.assertFalse(self.monday_config.is_pickup_allowed(13.0))
        
        # Test avec jour fermé
        self.assertFalse(self.sunday_config.is_pickup_allowed())
        self.assertFalse(self.sunday_config.is_pickup_allowed(10.0))
    
    def test_is_return_allowed(self):
        """Test de la méthode is_return_allowed"""
        # Test avec jour ouvert et heure valide
        self.assertTrue(self.monday_config.is_return_allowed(15.0))
        
        # Test avec jour ouvert et heure invalide
        self.assertFalse(self.monday_config.is_return_allowed(13.0))
        
        # Test avec jour fermé
        self.assertFalse(self.sunday_config.is_return_allowed())
        self.assertFalse(self.sunday_config.is_return_allowed(15.0))
