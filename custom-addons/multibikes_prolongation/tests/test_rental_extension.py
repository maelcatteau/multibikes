# -*- coding: utf-8 -*-
"""
Tests pour le module de prolongation de location
-----------------------------------------------
Ce fichier contient les tests unitaires et d'intégration pour
vérifier le bon fonctionnement du module de prolongation de location.
"""

from datetime import datetime, timedelta
from odoo.tests import tagged, Form
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError


@tagged("post_install", "-at_install")
class TestRentalExtension(TransactionCase):
    """
    Tests pour le module de prolongation de location
    """

    def setUp(self):
        """
        Configuration initiale pour les tests
        -----------------------------------
        Crée les données nécessaires pour les tests :
        - Produits de location
        - Client
        - Commande de location initiale
        """
        super(TestRentalExtension, self).setUp()

        # Créer un produit de location (vélo)
        self.product_bike = self.env["product.product"].create(
            {
                "name": "Vélo de test",
                "type": "product",
                "categ_id": self.env["product.category"]
                .create({"name": "Vélos de test"})
                .id,
                "rent_ok": True,
                "rental_pricing_ids": [
                    (
                        0,
                        0,
                        {
                            "duration": 1,
                            "unit": "day",
                            "price": 10.0,
                        },
                    )
                ],
                "standard_price": 100.0,
            }
        )

        # Créer un produit de location (accessoire)
        self.product_accessory = self.env["product.product"].create(
            {
                "name": "Casque de test",
                "type": "product",
                "categ_id": self.env["product.category"]
                .create({"name": "Accessoires de test"})
                .id,
                "rent_ok": True,
                "rental_pricing_ids": [
                    (
                        0,
                        0,
                        {
                            "duration": 1,
                            "unit": "day",
                            "price": 5.0,
                        },
                    )
                ],
                "standard_price": 50.0,
            }
        )

        # Créer un client
        self.partner = self.env["res.partner"].create(
            {
                "name": "Client Test",
                "email": "client.test@example.com",
            }
        )

        # Dates de location
        self.today = datetime.today().replace(hour=9, minute=0, second=0, microsecond=0)
        self.tomorrow = self.today + timedelta(days=1)
        self.in_three_days = self.today + timedelta(days=3)

        # Créer une commande de location
        self.rental_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "is_rental_order": True,
                "rental_start_date": self.today,
                "rental_return_date": self.in_three_days,
            }
        )

        # Ajouter des lignes de location
        self.rental_line_bike = self.env["sale.order.line"].create(
            {
                "order_id": self.rental_order.id,
                "product_id": self.product_bike.id,
                "product_uom_qty": 2.0,
                "is_rental": True,
                "rental_start_date": self.today,
                "rental_return_date": self.in_three_days,
            }
        )

        self.rental_line_accessory = self.env["sale.order.line"].create(
            {
                "order_id": self.rental_order.id,
                "product_id": self.product_accessory.id,
                "product_uom_qty": 1.0,
                "is_rental": True,
                "rental_start_date": self.today,
                "rental_return_date": self.in_three_days,
            }
        )

        # Confirmer la commande de location
        self.rental_order.action_confirm()

        # Simuler la livraison des articles
        for line in self.rental_order.order_line:
            line.qty_delivered = line.product_uom_qty

    def test_01_rental_extension_creation(self):
        """
        Test de la création d'une prolongation de location
        ------------------------------------------------
        Vérifie que l'assistant de prolongation peut être créé et
        que la commande de prolongation est correctement générée.
        """
        # Vérifier que la commande initiale n'a pas de prolongations
        self.assertEqual(
            self.rental_order.mb_extension_count,
            0,
            "La commande ne devrait pas avoir de prolongations initialement",
        )

        # Créer un assistant de prolongation
        wizard = self.env["rental.extension.wizard"].create(
            {
                "mb_order_id": self.rental_order.id,
                "mb_start_date": self.in_three_days,
                "mb_end_date": self.in_three_days + timedelta(days=2),
            }
        )

        # Créer des lignes pour l'assistant (tous les articles)
        for line in self.rental_order.order_line:
            self.env["rental.extension.wizard.line"].create(
                {
                    "mb_wizard_id": wizard.id,
                    "mb_order_line_id": line.id,
                    "mb_product_id": line.product_id.id,
                    "mb_product_name": line.name,
                    "mb_quantity": line.product_uom_qty,
                    "mb_uom_id": line.product_uom.id,
                    "mb_selected": True,
                }
            )

        # Créer la commande de prolongation
        result = wizard.create_extension_order()

        # Vérifier que la commande de prolongation a été créée
        self.assertEqual(
            self.rental_order.mb_extension_count,
            1,
            "Une prolongation devrait avoir été créée",
        )

        # Récupérer la commande de prolongation
        extension_order = self.rental_order.mb_rental_extensions_ids[0]

        # Vérifier les propriétés de la commande de prolongation
        self.assertTrue(
            extension_order.mb_is_rental_extension,
            "La commande devrait être marquée comme prolongation",
        )
        self.assertEqual(
            extension_order.mb_original_rental_id.id,
            self.rental_order.id,
            "La commande devrait référencer la commande d'origine",
        )
        self.assertEqual(
            extension_order.mb_rental_start_date,
            self.in_three_days,
            "La date de début devrait correspondre",
        )
        self.assertEqual(
            extension_order.mb_rental_return_date,
            self.in_three_days + timedelta(days=2),
            "La date de fin devrait correspondre",
        )

        # Vérifier que les articles ont été correctement ajoutés
        self.assertEqual(
            len(extension_order.order_line),
            2,
            "La commande de prolongation devrait avoir 2 lignes",
        )

        # Vérifier que les quantités livrées sont correctes
        for line in extension_order.order_line:
            self.assertEqual(
                line.qty_delivered,
                line.product_uom_qty,
                "Les articles devraient être marqués comme livrés",
            )

    def test_02_partial_extension(self):
        """
        Test d'une prolongation partielle
        -------------------------------
        Vérifie qu'il est possible de prolonger seulement une partie des articles
        et que les quantités sont correctement gérées.
        """
        # Créer un assistant de prolongation
        wizard = self.env["rental.extension.wizard"].create(
            {
                "mb_order_id": self.rental_order.id,
                "mb_start_date": self.in_three_days,
                "mb_end_date": self.in_three_days + timedelta(days=1),
            }
        )

        # Créer une seule ligne pour l'assistant (uniquement le vélo)
        self.env["rental.extension.wizard.line"].create(
            {
                "mb_wizard_id": wizard.id,
                "mb_order_line_id": self.rental_line_bike.id,
                "mb_product_id": self.product_bike.id,
                "mb_product_name": self.rental_line_bike.name,
                "mb_quantity": 1.0,  # Seulement 1 vélo sur les 2
                "mb_uom_id": self.rental_line_bike.product_uom.id,
                "mb_selected": True,
            }
        )

        # Créer la commande de prolongation
        result = wizard.create_extension_order()

        # Vérifier que la commande de prolongation a été créée
        extension_order = self.rental_order.mb_rental_extensions_ids[0]

        # Vérifier qu'il n'y a qu'une seule ligne dans la prolongation
        self.assertEqual(
            len(extension_order.order_line),
            1,
            "La commande de prolongation devrait avoir 1 ligne",
        )

        # Vérifier que c'est bien le vélo qui a été prolongé
        extension_line = extension_order.order_line[0]
        self.assertEqual(
            extension_line.product_id.id,
            self.product_bike.id,
            "Le produit prolongé devrait être le vélo",
        )
        self.assertEqual(
            extension_line.product_uom_qty, 1.0, "La quantité prolongée devrait être 1"
        )

        # Vérifier que la quantité retournée dans la commande d'origine est correcte
        self.assertEqual(
            self.rental_line_bike.qty_returned,
            1.0,
            "1 vélo devrait être marqué comme retourné",
        )
        self.assertEqual(
            self.rental_line_accessory.qty_returned,
            0.0,
            "L'accessoire ne devrait pas être marqué comme retourné",
        )

    def test_03_validation_errors(self):
        """
        Test des validations et erreurs
        -----------------------------
        Vérifie que les validations fonctionnent correctement et que
        les erreurs appropriées sont levées dans les cas problématiques.
        """
        # Test 1: Date de fin avant la date de début
        wizard = self.env["rental.extension.wizard"].create(
            {
                "mb_order_id": self.rental_order.id,
                "mb_start_date": self.in_three_days,
                "mb_end_date": self.in_three_days
                - timedelta(days=1),  # Date de fin avant la date de début
            }
        )

        # La validation devrait lever une erreur
        with self.assertRaises(UserError):
            wizard._onchange_dates()

        # Test 2: Quantité excessive
        wizard = self.env["rental.extension.wizard"].create(
            {
                "mb_order_id": self.rental_order.id,
                "mb_start_date": self.in_three_days,
                "mb_end_date": self.in_three_days + timedelta(days=1),
            }
        )

        # Créer une ligne avec une quantité excessive
        wizard_line = self.env["rental.extension.wizard.line"].create(
            {
                "mb_wizard_id": wizard.id,
                "mb_order_line_id": self.rental_line_bike.id,
                "mb_product_id": self.product_bike.id,
                "mb_product_name": self.rental_line_bike.name,
                "mb_quantity": 3.0,  # Plus que les 2 vélos loués
                "mb_uom_id": self.rental_line_bike.product_uom.id,
                "mb_selected": True,
            }
        )

        # La validation devrait lever une erreur
        with self.assertRaises(UserError):
            wizard_line._onchange_quantity()

    def test_04_multiple_extensions(self):
        """
        Test de prolongations multiples
        ----------------------------
        Vérifie qu'il est possible de créer plusieurs prolongations
        successives pour une même commande.
        """
        # Première prolongation
        wizard1 = self.env["rental.extension.wizard"].create(
            {
                "mb_order_id": self.rental_order.id,
                "mb_start_date": self.in_three_days,
                "mb_end_date": self.in_three_days + timedelta(days=2),
            }
        )

        # Créer des lignes pour l'assistant (tous les articles)
        for line in self.rental_order.order_line:
            self.env["rental.extension.wizard.line"].create(
                {
                    "mb_wizard_id": wizard1.id,
                    "mb_order_line_id": line.id,
                    "mb_product_id": line.product_id.id,
                    "mb_product_name": line.name,
                    "mb_quantity": line.product_uom_qty,
                    "mb_uom_id": line.product_uom.id,
                    "mb_selected": True,
                }
            )

        # Créer la première prolongation
        result1 = wizard1.create_extension_order()
        extension_order1 = self.rental_order.mb_rental_extensions_ids[0]

        # Deuxième prolongation (à partir de la première)
        wizard2 = self.env["rental.extension.wizard"].create(
            {
                "mb_order_id": extension_order1.id,
                "mb_start_date": extension_order1.rental_return_date,
                "mb_end_date": extension_order1.rental_return_date + timedelta(days=1),
            }
        )

        # Créer des lignes pour l'assistant (tous les articles)
        for line in extension_order1.order_line:
            self.env["rental.extension.wizard.line"].create(
                {
                    "mb_wizard_id": wizard2.id,
                    "mb_order_line_id": line.id,
                    "mb_product_id": line.product_id.id,
                    "mb_product_name": line.name,
                    "mb_quantity": line.product_uom_qty,
                    "mb_uom_id": line.product_uom.id,
                    "mb_selected": True,
                }
            )

        # Créer la deuxième prolongation
        result2 = wizard2.create_extension_order()

        # Vérifier que la première prolongation a elle-même une prolongation
        self.assertEqual(
            extension_order1.mb_extension_count,
            1,
            "La première prolongation devrait avoir une prolongation",
        )

        # Récupérer la deuxième prolongation
        extension_order2 = extension_order1.mb_rental_extensions_ids[0]

        # Vérifier les propriétés de la deuxième prolongation
        self.assertTrue(
            extension_order2.mb_is_rental_extension,
            "La commande devrait être marquée comme prolongation",
        )
        self.assertEqual(
            extension_order2.mb_original_rental_id.id,
            extension_order1.id,
            "La commande devrait référencer la première prolongation",
        )
        self.assertEqual(
            extension_order2.mb_rental_start_date,
            extension_order1.rental_return_date,
            "La date de début devrait correspondre",
        )
        self.assertEqual(
            extension_order2.mb_rental_return_date,
            extension_order1.rental_return_date + timedelta(days=1),
            "La date de fin devrait correspondre",
        )

    def test_05_has_rentable_lines(self):
        """
        Test du calcul de mb_has_rentable_lines
        ----------------------------------
        Vérifie que le champ mb_has_rentable_lines est correctement calculé
        dans différentes situations.
        """
        # Initialement, tous les articles sont livrés mais aucun n'est retourné
        self.assertTrue(
            self.rental_order.mb_has_rentable_lines,
            "La commande devrait avoir des articles prolongeables",
        )

        # Marquer tous les articles comme retournés
        for line in self.rental_order.order_line:
            line.qty_returned = line.qty_delivered

        # Recalculer mb_has_rentable_lines
        self.rental_order._compute_has_rentable_lines()

        # Vérifier que mb_has_rentable_lines est maintenant False
        self.assertFalse(
            self.rental_order.mb_has_rentable_lines,
            "La commande ne devrait plus avoir d'articles prolongeables",
        )

        # Marquer un seul article comme partiellement retourné
        self.rental_line_bike.qty_returned = 1.0  # Seulement 1 vélo sur 2 est retourné

        # Recalculer mb_has_rentable_lines
        self.rental_order._compute_has_rentable_lines()

        # Vérifier que mb_has_rentable_lines est à nouveau True
        self.assertTrue(
            self.rental_order.mb_has_rentable_lines,
            "La commande devrait avoir des articles prolongeables",
        )
