# -*- coding: utf-8 -*-
from odoo.tests import tagged
from .common import MultibikesWebsiteTestCommon as MultibikesWebsiteProductTestCommon
from datetime import datetime, timedelta
from unittest import mock

# Correction pour la compatibilité avec Odoo 18
try:
    from odoo.http import HttpRequest
except ImportError:
    # Alternative pour Odoo 18
    from werkzeug.wrappers import Request as HttpRequest


@tagged("post_install", "-at_install")
class TestProductTemplate(MultibikesWebsiteProductTestCommon):
    """Tests pour le modèle product.template avec les extensions multibikes_website"""

    def _mock_http_request(self):
        """Crée un mock de HttpRequest pour simuler l'environnement web"""
        request_mock = mock.MagicMock()
        request_mock.website = self.website
        return request_mock

    def test_get_additionnal_combination_info_non_rental(self):
        """Test de _get_additionnal_combination_info pour un produit non louable"""
        # Pour un produit non louable, la méthode devrait retourner le résultat de super() sans modifications
        # Préparer le contexte
        date = datetime.today()
        quantity = 1

        # Appeler la méthode
        result = self.non_rental_product_template._get_additionnal_combination_info(
            self.non_rental_product, quantity, date, self.website
        )

        # Vérifier que la clé is_rental n'est pas présente ou est False
        self.assertNotIn("is_rental", result)

    def test_get_additionnal_combination_info_rental_no_dates(self):
        """Test de _get_additionnal_combination_info pour un produit louable sans dates spécifiées"""
        # Simuler l'environnement HTTP
        with mock.patch("odoo.http.request") as mock_request:
            mock_request.website = self.website
            # Créer un order vide
            order = self.env["sale.order"].create(
                {
                    "partner_id": self.env.ref("base.partner_admin").id,
                    "company_id": self.test_company.id,
                }
            )
            mock_request.website.sale_get_order.return_value = order

            # Appeler la méthode
            quantity = 1
            date = datetime.today()

            result = self.rental_product_template._get_additionnal_combination_info(
                self.rental_product, quantity, date, self.website
            )

            # Vérifier les résultats
            self.assertTrue(
                result.get("is_rental"), "Le produit devrait être marqué comme louable"
            )

            # Vérifier que la pricing_table ne contient que les tarifs publiés
            pricing_table = result.get("pricing_table", [])
            pricing_names = [p[0] for p in pricing_table]

            # Doit inclure les tarifs publiés
            self.assertIn(
                self.pricing_hour.name,
                pricing_names,
                "Le tarif horaire (publié) devrait être inclus",
            )
            self.assertIn(
                self.pricing_day.name,
                pricing_names,
                "Le tarif journalier (publié) devrait être inclus",
            )

            # Ne doit pas inclure les tarifs non publiés
            self.assertNotIn(
                self.pricing_week.name,
                pricing_names,
                "Le tarif hebdomadaire (non publié) ne devrait pas être inclus",
            )

    def test_get_additionnal_combination_info_rental_with_dates(self):
        """Test de _get_additionnal_combination_info pour un produit louable avec dates spécifiées"""
        # Simuler l'environnement HTTP
        with mock.patch("odoo.http.request") as mock_request:
            mock_request.website = self.website
            # Créer un order avec des dates de location
            start_date = datetime.now()
            end_date = start_date + timedelta(days=2)

            order = self.env["sale.order"].create(
                {
                    "partner_id": self.env.ref("base.partner_admin").id,
                    "company_id": self.test_company.id,
                    "rental_start_date": start_date,
                    "rental_return_date": end_date,
                }
            )
            mock_request.website.sale_get_order.return_value = order

            # Appeler la méthode
            quantity = 1
            date = datetime.today()

            result = self.rental_product_template._get_additionnal_combination_info(
                self.rental_product, quantity, date, self.website
            )

            # Vérifier les résultats
            self.assertTrue(
                result.get("is_rental"), "Le produit devrait être marqué comme louable"
            )

            # Vérifier les dates par défaut
            self.assertTrue(
                "default_start_date" in result,
                "Les dates par défaut devraient être définies",
            )
            self.assertTrue(
                "default_end_date" in result,
                "Les dates par défaut devraient être définies",
            )

            # Vérifier que la durée actuelle est correcte (2 jours)
            self.assertEqual(
                result.get("current_rental_duration"),
                2,
                "La durée de location devrait être de 2 jours",
            )

            # Vérifier que la pricing_table ne contient que les tarifs publiés
            pricing_table = result.get("pricing_table", [])
            pricing_names = [p[0] for p in pricing_table]

            # Doit inclure les tarifs publiés
            self.assertIn(
                self.pricing_hour.name,
                pricing_names,
                "Le tarif horaire (publié) devrait être inclus",
            )
            self.assertIn(
                self.pricing_day.name,
                pricing_names,
                "Le tarif journalier (publié) devrait être inclus",
            )

            # Ne doit pas inclure les tarifs non publiés
            self.assertNotIn(
                self.pricing_week.name,
                pricing_names,
                "Le tarif hebdomadaire (non publié) ne devrait pas être inclus",
            )

    def test_get_additionnal_combination_info_with_all_pricing_published(self):
        """Test avec tous les tarifs publiés"""
        # Publier tous les tarifs
        self.pricing_week.mb_website_published = True

        # Appeler la méthode
        quantity = 1
        date = datetime.today()

        # Patch du proxy request via odoo.http
        from odoo import http

        with mock.patch.object(http, "request", create=True) as mock_request:
            mock_request.website = self.website
            order = self.env["sale.order"].create(
                {
                    "partner_id": self.env.ref("base.partner_admin").id,
                    "company_id": self.main_company.id,
                }
            )
            mock_request.website.sale_get_order.return_value = order

            result = self.rental_product_template._get_additionnal_combination_info(
                self.rental_product, quantity, date, self.website
            )

        # Vérifier que tous les tarifs sont inclus
        pricing_table = result.get("pricing_table", [])
        pricing_names = [p[0] for p in pricing_table]

        self.assertIn(self.pricing_hour.name, pricing_names)
        self.assertIn(self.pricing_day.name, pricing_names)
        self.assertIn(self.pricing_week.name, pricing_names)

        # Vérifier que le nombre de tarifs est correct
        self.assertEqual(
            len(pricing_table), 3, "Les trois tarifs devraient être inclus"
        )
