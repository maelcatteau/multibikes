# -*- coding: utf-8 -*-
from odoo.tests import tagged
from .common import MultibikesWebsiteTestCommon as MultibikesWebsiteConfigTestCommon
from datetime import timedelta

@tagged('post_install', '-at_install')
class TestResConfigSettings(MultibikesWebsiteConfigTestCommon):
    """Tests pour le modèle res.config.settings avec les extensions multibikes_website"""
    
    def test_config_settings_renting_periods(self):
        """Test du champ related renting_periods dans les paramètres de configuration"""
        # Créer un enregistrement de configuration
        config = self.env['res.config.settings'].create({
            'company_id': self.main_company.id,
        })
        
        # Vérifier que les périodes de location sont correctement chargées
        # Note: les champs related sont généralement chargés après un onchange ou un save
        config = config.sudo()  # Pour éviter les problèmes d'accès
        
        # Tester avec les ID existants
        self.assertEqual(len(config.renting_periods), 3, 
                        "Les paramètres de configuration devraient avoir 3 périodes de location")
        
        period_ids = config.renting_periods.ids
        self.assertIn(self.current_period.id, period_ids)
        self.assertIn(self.future_period.id, period_ids)
        self.assertIn(self.past_period.id, period_ids)
    
    def test_config_settings_add_renting_period(self):
        """Test de l'ajout d'une période de location via les paramètres de configuration"""
        # Créer un enregistrement de configuration
        config = self.env['res.config.settings'].create({
            'company_id': self.main_company.id,
        })
        config = config.sudo()
        
        # Nombre initial de périodes
        initial_count = len(self.main_company.renting_periods)
        
        # Créer une nouvelle période
        new_period_values = {
            'name': 'Nouvelle Période',
            'start_date': self.next_month,
            'end_date': self.next_month + timedelta(days=30),
            'minimal_time_duration': 5,
            'minimal_time_unit': 'day',
            'is_closed': False,
            'company_id': self.main_company.id,
        }
        
        # Ajouter la période via les paramètres de configuration
        new_period = self.env['mb.renting.period'].create(new_period_values)
        config.renting_periods = [(4, new_period.id)]
        
        # Enregistrer les paramètres
        config.execute()
        
        # Vérifier que la période a été ajoutée à la société
        updated_periods = self.main_company.renting_periods
        self.assertEqual(len(updated_periods), initial_count + 1, 
                        "Une nouvelle période devrait avoir été ajoutée")
        self.assertIn(new_period.id, updated_periods.ids, 
                     "La nouvelle période devrait être associée à la société")
    
    def test_config_settings_remove_renting_period(self):
        """Test de la suppression d'une période de location via les paramètres de configuration"""
        # Créer un enregistrement de configuration
        config = self.env['res.config.settings'].create({
            'company_id': self.main_company.id,
        })
        config = config.sudo()
        
        # Nombre initial de périodes
        initial_count = len(self.main_company.renting_periods)
        
        # Supprimer la période passée via les paramètres de configuration
        config.renting_periods = [(3, self.past_period.id)]  # Command 3: remove this ID, but do not delete it
        
        # Enregistrer les paramètres
        config.execute()
        
        # Vérifier que la période a été retirée de la société
        updated_periods = self.main_company.renting_periods
        self.assertEqual(len(updated_periods), initial_count - 1, 
                        "Une période devrait avoir été retirée")
        self.assertNotIn(self.past_period.id, updated_periods.ids, 
                        "La période passée ne devrait plus être associée à la société")
        
        # Vérifier que la période existe toujours dans la base de données
        period_exists = self.env['mb.renting.period'].browse(self.past_period.id).exists()
        self.assertTrue(period_exists, 
                       "La période devrait toujours exister dans la base de données")
