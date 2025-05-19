# -*- coding: utf-8 -*-
from odoo.tests import tagged
from .common import MultibikesWebsiteTestCommon as MultibikesWebsiteConfigTestCommon
from datetime import date, timedelta

@tagged('post_install', '-at_install')
class TestResCompany(MultibikesWebsiteConfigTestCommon):
    """Tests pour le modèle res.company avec les extensions multibikes_website"""
    
    def test_renting_periods_field(self):
        """Test du champ renting_periods - relation one2many avec mb.renting.period"""
        # Vérifier que les périodes sont correctement associées à la société principale
        main_company_periods = self.main_company.renting_periods
        
        # Vérifier le nombre de périodes
        self.assertEqual(len(main_company_periods), 3, 
                        "La société principale devrait avoir 3 périodes de location")
        
        # Vérifier que les périodes attendues sont présentes
        period_names = main_company_periods.mapped('name')
        self.assertIn('Période Actuelle', period_names)
        self.assertIn('Période Future', period_names)
        self.assertIn('Période Passée', period_names)
        
        # Vérifier que les périodes d'une autre société ne sont pas incluses
        self.assertNotIn(self.second_company_period.id, main_company_periods.ids)
        
        # Vérifier les périodes de la deuxième société
        second_company_periods = self.second_company.renting_periods
        self.assertEqual(len(second_company_periods), 1, 
                        "La deuxième société devrait avoir 1 période de location")
        self.assertEqual(second_company_periods[0].id, self.second_company_period.id)
    
    def test_get_dynamic_renting_minimal_duration_current_period(self):
        """Test de get_dynamic_renting_minimal_duration avec une date dans la période actuelle"""
        # Test avec la date d'aujourd'hui (qui devrait être dans la période actuelle)
        result = self.main_company.get_dynamic_renting_minimal_duration(self.today)
        
        # Vérifier les valeurs retournées
        self.assertEqual(result['duration'], 2, "La durée minimale devrait être de 2")
        self.assertEqual(result['unit'], 'day', "L'unité devrait être 'day'")
        self.assertEqual(result['start_date'], self.last_week)
        self.assertEqual(result['end_date'], self.next_week)
    
    def test_get_dynamic_renting_minimal_duration_future_period(self):
        """Test de get_dynamic_renting_minimal_duration avec une date dans la période future"""
        # Test avec une date située dans la période future
        reference_date = self.tomorrow + timedelta(days=1)  # Pour être sûr d'être dans la période future
        result = self.main_company.get_dynamic_renting_minimal_duration(reference_date)
        
        # Vérifier les valeurs retournées
        self.assertEqual(result['duration'], 3, "La durée minimale devrait être de 3")
        self.assertEqual(result['unit'], 'day', "L'unité devrait être 'day'")
        self.assertEqual(result['start_date'], self.tomorrow)
        self.assertEqual(result['end_date'], self.next_month)
    
    def test_get_dynamic_renting_minimal_duration_no_period(self):
        """Test de get_dynamic_renting_minimal_duration avec une date sans période correspondante"""
        # Test avec une date très future (après toutes les périodes définies)
        reference_date = self.next_month + timedelta(days=60)
        result = self.main_company.get_dynamic_renting_minimal_duration(reference_date)
        
        # Vérifier les valeurs par défaut
        self.assertEqual(result['duration'], 1, "La durée minimale par défaut devrait être de 1")
        self.assertEqual(result['unit'], 'day', "L'unité par défaut devrait être 'day'")
        self.assertIsNone(result['start_date'], "Il ne devrait pas y avoir de date de début")
        self.assertIsNone(result['end_date'], "Il ne devrait pas y avoir de date de fin")
    
    def test_get_dynamic_renting_minimal_duration_default_date(self):
        """Test de get_dynamic_renting_minimal_duration avec la date par défaut (aujourd'hui)"""
        # Test sans spécifier de date (devrait utiliser la date d'aujourd'hui)
        result = self.main_company.get_dynamic_renting_minimal_duration()
        
        # La date d'aujourd'hui devrait correspondre à la période actuelle
        self.assertEqual(result['duration'], 2, "La durée minimale devrait être de 2")
        self.assertEqual(result['unit'], 'day', "L'unité devrait être 'day'")
        self.assertEqual(result['start_date'], self.last_week)
        self.assertEqual(result['end_date'], self.next_week)
    
    def test_get_dynamic_renting_minimal_duration_other_company(self):
        """Test de get_dynamic_renting_minimal_duration pour une autre société"""
        # Test pour la deuxième société
        result = self.second_company.get_dynamic_renting_minimal_duration(self.today)
        
        # Vérifier les valeurs retournées
        self.assertEqual(result['duration'], 4, "La durée minimale devrait être de 4")
        self.assertEqual(result['unit'], 'hour', "L'unité devrait être 'hour'")
        self.assertEqual(result['start_date'], self.last_week)
        self.assertEqual(result['end_date'], self.next_week)
