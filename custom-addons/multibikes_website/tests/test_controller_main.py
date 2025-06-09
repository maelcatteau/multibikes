# -*- coding: utf-8 -*-

from odoo.tests import HttpCase, tagged
from odoo.addons.website.tools import MockRequest
from unittest.mock import patch
import json
from datetime import datetime, timedelta
from odoo import fields


@tagged('post_install', '-at_install')
class TestWebsiteSaleRentingCustom(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Créer des données de test
        cls.company = cls.env.ref('base.main_company')

        # Créer ou utiliser une récurrence existante
        cls.recurrence = cls.env['sale.temporal.recurrence'].search([], limit=1)
        if not cls.recurrence:
            cls.recurrence = cls.env['sale.temporal.recurrence'].create({
                'name': 'Récurrence Test',
                'duration': 2,
                'unit': 'hour',
            })

        # Créer une période de location avec la récurrence
        cls.rental_period = cls.env['mb.renting.period'].create({
            'name': 'Période Test',
            'start_date': fields.Date.today(),
            'end_date': fields.Date.today() + timedelta(days=30),
            'company_id': cls.company.id,
            'is_closed': False,
            'recurrence_id': cls.recurrence.id,
        })

        # Créer des configurations de jour
        cls.day_config_monday = cls.env['mb.renting.day.config'].create({
            'period_id': cls.rental_period.id,
            'day_of_week': '1',  # Lundi
            'is_open': True,
            'allow_pickup': True,
            'pickup_hour_from': 9.0,
            'pickup_hour_to': 18.0,
            'allow_return': True,
            'return_hour_from': 8.0,
            'return_hour_to': 19.0,
        })

        cls.day_config_sunday = cls.env['mb.renting.day.config'].create({
            'period_id': cls.rental_period.id,
            'day_of_week': '7',  # Dimanche
            'is_open': False,
            'allow_pickup': False,
            'pickup_hour_from': 0.0,
            'pickup_hour_to': 0.0,
            'allow_return': False,
            'return_hour_from': 0.0,
            'return_hour_to': 0.0,
        })

        # Créer un site web pour les tests
        cls.website = cls.env['website'].search([], limit=1)
        if not cls.website:
            cls.website = cls.env['website'].create({
                'name': 'Test Website',
                'domain': 'test.local',
                'tz': 'Europe/Paris',
            })

    def test_renting_product_constraints_route_exists(self):
        """Test que la route JSON est accessible."""
        response = self.url_open(
            '/rental/product/constraints',
            data=json.dumps({}),
            headers={'Content-Type': 'application/json'}
        )
        self.assertEqual(response.status_code, 200)

    def test_renting_product_constraints_response_structure(self):
        """Test la structure de la réponse JSON."""
        with MockRequest(self.env, website=self.website):
            from odoo.addons.multibikes_website.controllers.main import WebsiteSaleRentingCustom
            controller = WebsiteSaleRentingCustom()

            result = controller.renting_product_constraints()

            # Vérifier la structure de base
            self.assertIn('renting_periods', result)
            self.assertIn('website_tz', result)
            self.assertIn('renting_minimal_time', result)

            # Vérifier le timezone
            self.assertEqual(result['website_tz'], 'Europe/Paris')

            # Vérifier le temps minimal par défaut
            self.assertEqual(result['renting_minimal_time']['duration'], '1')
            self.assertEqual(result['renting_minimal_time']['unit'], 'hour')

    def test_get_rental_periods_basic(self):
        """Test la méthode _get_rental_periods."""
        with MockRequest(self.env, website=self.website):
            from odoo.addons.multibikes_website.controllers.main import WebsiteSaleRentingCustom
            controller = WebsiteSaleRentingCustom()

            periods_data = controller._get_rental_periods()

            # Vérifier qu'on a au moins une période (celle créée dans setUpClass)
            self.assertTrue(len(periods_data) >= 1)

            # Trouver notre période test
            test_period = next((p for p in periods_data if p['name'] == 'Période Test'), None)
            self.assertIsNotNone(test_period)

            # Vérifier la structure de la période
            self.assertIn('id', test_period)
            self.assertIn('name', test_period)
            self.assertIn('start_date', test_period)
            self.assertIn('end_date', test_period)
            self.assertIn('is_closed', test_period)
            self.assertIn('minimal_time', test_period)
            self.assertIn('day_configs', test_period)

            # Vérifier les valeurs
            self.assertEqual(test_period['name'], 'Période Test')
            self.assertEqual(test_period['is_closed'], False)

    def test_get_rental_periods_date_filtering(self):
        """Test le filtrage par dates des périodes."""
        # Créer une période expirée
        expired_recurrence = self.env['sale.temporal.recurrence'].create({
            'name': 'Récurrence Expirée',
            'duration': 1,
            'unit': 'day',
        })

        expired_period = self.env['mb.renting.period'].create({
            'name': 'Période Expirée',
            'start_date': fields.Date.today() - timedelta(days=60),
            'end_date': fields.Date.today() - timedelta(days=30),
            'company_id': self.company.id,
            'is_closed': False,
            'recurrence_id': expired_recurrence.id,
        })

        with MockRequest(self.env, website=self.website):
            from odoo.addons.multibikes_website.controllers.main import WebsiteSaleRentingCustom
            controller = WebsiteSaleRentingCustom()

            periods_data = controller._get_rental_periods()
            period_names = [p['name'] for p in periods_data]

            # La période expirée ne doit pas apparaître
            self.assertNotIn('Période Expirée', period_names)
            # La période active doit apparaître
            self.assertIn('Période Test', period_names)

    def test_get_rental_periods_company_filtering(self):
        """Test le filtrage par société."""
        # Créer une autre société
        other_company = self.env['res.company'].create({
            'name': 'Autre Société Test',
        })

        other_recurrence = self.env['sale.temporal.recurrence'].create({
            'name': 'Récurrence Autre',
            'duration': 1,
            'unit': 'day',
        })

        other_period = self.env['mb.renting.period'].create({
            'name': 'Période Autre Société',
            'start_date': fields.Date.today(),
            'end_date': fields.Date.today() + timedelta(days=30),
            'company_id': other_company.id,
            'is_closed': False,
            'recurrence_id': other_recurrence.id,
        })

        with MockRequest(self.env, website=self.website):
            from odoo.addons.multibikes_website.controllers.main import WebsiteSaleRentingCustom
            controller = WebsiteSaleRentingCustom()

            periods_data = controller._get_rental_periods()
            period_names = [p['name'] for p in periods_data]

            # Seules les périodes de la société courante doivent apparaître
            self.assertIn('Période Test', period_names)
            self.assertNotIn('Période Autre Société', period_names)

    def test_format_day_configs(self):
        """Test le formatage des configurations de jour."""
        with MockRequest(self.env, website=self.website):
            from odoo.addons.multibikes_website.controllers.main import WebsiteSaleRentingCustom
            controller = WebsiteSaleRentingCustom()

            formatted_configs = controller._format_day_configs(self.rental_period.day_configs_ids)

            # Vérifier que c'est un dictionnaire
            self.assertIsInstance(formatted_configs, dict)

            # Vérifier la configuration du lundi
            self.assertIn('0', formatted_configs)  # Lundi
            monday_config = formatted_configs['0']

            self.assertEqual(monday_config['is_open'], True)
            self.assertEqual(monday_config['pickup']['allowed'], True)
            self.assertEqual(monday_config['pickup']['hour_from'], 9.0)
            self.assertEqual(monday_config['pickup']['hour_to'], 18.0)
            self.assertEqual(monday_config['return']['allowed'], True)

            # Vérifier la configuration du dimanche
            self.assertIn('6', formatted_configs)  # Dimanche
            sunday_config = formatted_configs['6']

            self.assertEqual(sunday_config['is_open'], False)
            self.assertEqual(sunday_config['pickup']['allowed'], False)
            self.assertEqual(sunday_config['return']['allowed'], False)

    def test_minimal_time_data_structure(self):
        """Test la structure des données de temps minimal."""
        with MockRequest(self.env, website=self.website):
            from odoo.addons.multibikes_website.controllers.main import WebsiteSaleRentingCustom
            controller = WebsiteSaleRentingCustom()

            periods_data = controller._get_rental_periods()
            test_period = next((p for p in periods_data if p['name'] == 'Période Test'), None)

            self.assertIsNotNone(test_period)
            self.assertIn('minimal_time', test_period)

            minimal_time = test_period['minimal_time']
            self.assertIn('duration', minimal_time)
            self.assertIn('unit', minimal_time)
            self.assertIn('name', minimal_time)

    @patch('odoo.http.request')
    def test_mocked_request_environment(self, mock_request):
        """Test avec un environnement de requête mocké."""
        # Configuration du mock
        mock_request.env = self.env
        mock_request.website = self.website
        mock_request.env.company = self.company

        from odoo.addons.multibikes_website.controllers.main import WebsiteSaleRentingCustom
        controller = WebsiteSaleRentingCustom()

        result = controller.renting_product_constraints()

        # Vérifications de base
        self.assertIsInstance(result, dict)
        self.assertIn('renting_periods', result)
        self.assertEqual(result['website_tz'], 'Europe/Paris')

        # Vérifier que nos données de test sont présentes
        period_names = [p['name'] for p in result['renting_periods']]
        self.assertIn('Période Test', period_names)

    def tearDown(self):
        """Nettoyage après chaque test."""
        super().tearDown()
        # Les données créées en setUpClass seront automatiquement supprimées
        # après la suite de tests
