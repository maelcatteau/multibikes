# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import HttpCase
from datetime import date, timedelta
import json
from .common import MultibikesWebsiteTestCommon

@tagged('post_install', '-at_install', 'multibikes_controller')
class TestWebsiteSaleRentingCustomController(HttpCase, MultibikesWebsiteTestCommon):
    """Test du contrôleur WebsiteSaleRentingCustom"""

    def setUp(self):
        super(TestWebsiteSaleRentingCustomController, self).setUp()
        # Assurez-vous que nous avons un utilisateur pour les tests HTTP
        self.user_admin = self.env.ref('base.user_admin')
        self.authenticate('admin', 'admin')

    def test_renting_product_constraints(self):
        """Test de la route /rental/product/constraints"""
        # Préparation des données pour le test
        today = date.today()
        end_date = today + timedelta(days=3*365)
        
        # Création de périodes de test supplémentaires pour différents scénarios
        future_period = self.env['mb.renting.period'].create({
            'name': 'Future Period',
            'company_id': self.main_company.id,
            'start_date': today + timedelta(days=30),
            'end_date': today + timedelta(days=60),
            'minimal_time_duration': 3,
            'minimal_time_unit': 'day',
            'is_closed': False,
        })
        
        # Ajout de configurations de jours pour cette période
        self.env['mb.renting.day.config'].create({
            'period_id': future_period.id,
            'company_id': self.main_company.id,
            'day_of_week': '1',  # Mardi
            'is_open': True,
            'allow_pickup': True,
            'pickup_hour_from': 10.0,
            'pickup_hour_to': 18.0,
            'allow_return': True,
            'return_hour_from': 10.0,
            'return_hour_to': 18.0,
        })
        
        # Période fermée
        closed_period = self.env['mb.renting.period'].create({
            'name': 'Closed Period',
            'company_id': self.main_company.id,
            'start_date': today + timedelta(days=90),
            'end_date': today + timedelta(days=100),
            'minimal_time_duration': 1,
            'minimal_time_unit': 'day',
            'is_closed': True,
        })
        
        # Appel à la route JSON simulant une requête AJAX
        url = '/rental/product/constraints'
        response = self.url_open(url, data=json.dumps({}), headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        self.assertEqual(response.status_code, 200, "La route devrait répondre avec un statut HTTP 200")
        
        # Analyser la réponse JSON
        result = json.loads(response.content)
        
        # Vérifier la structure de la réponse
        self.assertIn('all_periods', result, "La réponse devrait contenir 'all_periods'")
        
        # Vérifier que toutes nos périodes sont présentes
        period_ids = [p['id'] for p in result['all_periods']]
        self.assertIn(self.current_period.id, period_ids, "La période actuelle devrait être dans la réponse")
        self.assertIn(future_period.id, period_ids, "La période future devrait être dans la réponse")
        self.assertIn(closed_period.id, period_ids, "La période fermée devrait être dans la réponse")
        
        # Vérifier le contenu d'une période spécifique
        for period_data in result['all_periods']:
            if period_data['id'] == future_period.id:
                self.assertEqual(period_data['name'], 'Future Period')
                self.assertEqual(period_data['minimal_time_duration'], 3)
                self.assertEqual(period_data['minimal_time_unit'], 'day')
                self.assertFalse(period_data['is_closed'])
                
                # Vérifier les configurations de jour
                self.assertIn('day_configs', period_data)
                self.assertIn('1', period_data['day_configs'])  # Mardi
                day_config = period_data['day_configs']['1']
                self.assertTrue(day_config['is_open'])
                self.assertTrue(day_config['allow_pickup'])
                self.assertEqual(day_config['pickup_hour_from'], 10.0)
                self.assertEqual(day_config['pickup_hour_to'], 18.0)
        
        # Vérifier que seules les périodes dans l'intervalle sont retournées
        for period_data in result['all_periods']:
            period_start = date.fromisoformat(period_data['start_date'])
            period_end = date.fromisoformat(period_data['end_date'])
            self.assertTrue(
                period_end >= today and period_start <= end_date,
                "Les dates des périodes devraient être dans l'intervalle spécifié"
            )
