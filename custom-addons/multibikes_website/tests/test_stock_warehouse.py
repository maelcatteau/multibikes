# -*- coding: utf-8 -*-
from odoo.tests import tagged
from .common import MultibikesWebsiteTestCommon as MultibikesWebsiteConfigTestCommon
from datetime import datetime, timedelta


@tagged("post_install", "-at_install")
class TestStockWarehouse(MultibikesWebsiteConfigTestCommon):
    """Tests pour le modèle stock.warehouse avec les extensions multibikes_website"""

    def setUp(self):
        super(TestStockWarehouse, self).setUp()
        # Définir self.product comme référence à un produit existant
        self.product = self.rental_product

    def test_is_excluded_from_availability_field(self):
        """Test du champ is_excluded_from_availability"""
        # Vérifier les valeurs initiales
        self.assertFalse(
            self.main_warehouse.is_excluded_from_availability,
            "L'entrepôt principal ne devrait pas être exclu par défaut",
        )
        self.assertFalse(
            self.secondary_warehouse.is_excluded_from_availability,
            "L'entrepôt secondaire ne devrait pas être exclu par défaut",
        )
        self.assertTrue(
            self.excluded_warehouse.is_excluded_from_availability,
            "L'entrepôt exclu devrait être marqué comme exclu",
        )

    def test_modify_is_excluded_from_availability(self):
        """Test de la modification du champ is_excluded_from_availability"""
        # Modifier les valeurs
        self.main_warehouse.is_excluded_from_availability = True
        self.excluded_warehouse.is_excluded_from_availability = False

        # Vérifier les nouvelles valeurs
        self.assertTrue(
            self.main_warehouse.is_excluded_from_availability,
            "L'entrepôt principal devrait maintenant être exclu",
        )
        self.assertFalse(
            self.excluded_warehouse.is_excluded_from_availability,
            "L'entrepôt exclu ne devrait plus être marqué comme exclu",
        )

    def test_impact_on_product_availability(self):
        """Test de l'impact de l'exclusion d'un entrepôt sur les disponibilités des produits"""
        # Définir les dates de test
        start_date = datetime.now()
        end_date = start_date + timedelta(days=1)

        # Vérifier les disponibilités avant exclusion/inclusion
        initial_availabilities = self.product._get_availabilities(
            start_date, end_date, warehouse_id=False
        )

        # Marquer l'entrepôt secondaire comme exclu
        self.secondary_warehouse.is_excluded_from_availability = True

        # Vérifier les disponibilités après exclusion
        availabilities_after_exclusion = self.product._get_availabilities(
            start_date, end_date, warehouse_id=False
        )

        # La quantité disponible devrait être diminuée du stock de l'entrepôt secondaire (3 unités)
        # Note: cette comparaison suppose que l'implémentation de _get_availabilities tient bien compte
        # du flag is_excluded_from_availability
        self.assertTrue(
            initial_availabilities[0]["quantity_available"]
            > availabilities_after_exclusion[0]["quantity_available"],
            "La quantité disponible devrait diminuer après avoir exclu un entrepôt",
        )

        # La diminution devrait correspondre au stock de l'entrepôt secondaire
        expected_diff = 3.0  # Stock de l'entrepôt secondaire
        actual_diff = (
            initial_availabilities[0]["quantity_available"]
            - availabilities_after_exclusion[0]["quantity_available"]
        )
        self.assertEqual(
            actual_diff,
            expected_diff,
            f"La différence de quantité disponible devrait être de {expected_diff}",
        )

    def test_warehouse_exclusion_with_specific_warehouse(self):
        """Test de l'exclusion d'entrepôts lorsqu'un entrepôt spécifique est demandé"""
        # Définir les dates de test
        start_date = datetime.now()
        end_date = start_date + timedelta(days=1)

        # Vérifier les disponibilités pour l'entrepôt principal spécifiquement
        main_warehouse_availabilities = self.product._get_availabilities(
            start_date, end_date, warehouse_id=self.main_warehouse.id
        )

        # Vérifier que la quantité correspond au stock de l'entrepôt principal
        expected_qty = 5.0  # Stock de l'entrepôt principal
        self.assertEqual(
            main_warehouse_availabilities[0]["quantity_available"],
            expected_qty,
            f"La quantité disponible dans l'entrepôt principal devrait être de {expected_qty}",
        )

        # Même si l'entrepôt principal est marqué comme exclu, sa quantité devrait être disponible
        # si on le demande spécifiquement
        self.main_warehouse.is_excluded_from_availability = True

        main_warehouse_availabilities_after_exclusion = (
            self.product._get_availabilities(
                start_date, end_date, warehouse_id=self.main_warehouse.id
            )
        )

        # La quantité disponible devrait rester inchangée
        self.assertEqual(
            main_warehouse_availabilities_after_exclusion[0]["quantity_available"],
            expected_qty,
            "La quantité disponible ne devrait pas changer quand on demande spécifiquement l'entrepôt",
        )
