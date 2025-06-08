# -*- coding: utf-8 -*-
"""Tests for Stock Warehouse extension in multibikes_website module."""
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger
from psycopg2 import IntegrityError


class TestStockWarehouse(TransactionCase):
    """Test cases for StockWarehouse model extensions."""

    @classmethod
    def setUpClass(cls):
        """Set up test data."""
        super().setUpClass()

        # Créer des compagnies de test
        cls.company_1 = cls.env['res.company'].create({
            'name': 'Test Company 1',
        })

        cls.company_2 = cls.env['res.company'].create({
            'name': 'Test Company 2',
        })

        # Créer des entrepôts de test
        cls.warehouse_1 = cls.env['stock.warehouse'].create({
            'name': 'Warehouse 1',
            'code': 'WH1',
            'company_id': cls.company_1.id,
        })

        cls.warehouse_2 = cls.env['stock.warehouse'].create({
            'name': 'Warehouse 2',
            'code': 'WH2',
            'company_id': cls.company_1.id,
        })

        cls.warehouse_3 = cls.env['stock.warehouse'].create({
            'name': 'Warehouse 3',
            'code': 'WH3',
            'company_id': cls.company_2.id,
        })

    def setUp(self):
        """Reset warehouse configurations before each test."""
        super().setUp()
        # Réinitialiser les configurations
        warehouses = self.env['stock.warehouse'].search([])
        warehouses.write({
            'is_main_rental_warehouse': False,
            'is_winter_storage_warehouse': False,
        })

    def test_default_values(self):
        """Test that default values are correctly set."""
        warehouse = self.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TEST',
            'company_id': self.company_1.id,
        })

        self.assertFalse(warehouse.is_main_rental_warehouse)
        self.assertFalse(warehouse.is_winter_storage_warehouse)

    def test_set_main_rental_warehouse(self):
        """Test setting an warehouse as main rental warehouse."""
        self.warehouse_1.is_main_rental_warehouse = True

        self.assertTrue(self.warehouse_1.is_main_rental_warehouse)
        self.assertFalse(self.warehouse_1.is_winter_storage_warehouse)

    def test_set_winter_storage_warehouse(self):
        """Test setting an warehouse as winter storage warehouse."""
        self.warehouse_1.is_winter_storage_warehouse = True

        self.assertTrue(self.warehouse_1.is_winter_storage_warehouse)
        self.assertFalse(self.warehouse_1.is_main_rental_warehouse)

    def test_warehouse_types_exclusivity_constraint(self):
        """Test that a warehouse cannot be both main rental and winter storage."""
        self.warehouse_1.is_main_rental_warehouse = True

        with self.assertRaises(ValidationError) as context:
            self.warehouse_1.is_winter_storage_warehouse = True

        self.assertIn("ne peut pas être à la fois", str(context.exception))

    def test_warehouse_types_exclusivity_constraint_reverse(self):
        """Test exclusivity constraint when setting main rental after winter storage."""
        self.warehouse_1.is_winter_storage_warehouse = True

        with self.assertRaises(ValidationError) as context:
            self.warehouse_1.is_main_rental_warehouse = True

        self.assertIn("ne peut pas être à la fois", str(context.exception))

    def test_unique_main_rental_warehouse_per_company(self):
        """Test that only one main rental warehouse is allowed per company."""
        self.warehouse_1.is_main_rental_warehouse = True

        with mute_logger('odoo.sql_db'):  # Supprime les logs d'erreur SQL
            with self.assertRaises(IntegrityError):
                self.warehouse_2.is_main_rental_warehouse = True

    def test_unique_winter_storage_warehouse_per_company(self):
        """Test that only one winter storage warehouse is allowed per company."""
        self.warehouse_1.is_winter_storage_warehouse = True

        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                self.warehouse_2.is_winter_storage_warehouse = True

    def test_different_companies_can_have_same_types(self):
        """Test that different companies can each have their own main/winter warehouses."""
        # Compagnie 1 - entrepôt principal
        self.warehouse_1.is_main_rental_warehouse = True

        # Compagnie 2 - entrepôt principal (devrait fonctionner)
        self.warehouse_3.is_main_rental_warehouse = True

        self.assertTrue(self.warehouse_1.is_main_rental_warehouse)
        self.assertTrue(self.warehouse_3.is_main_rental_warehouse)

        # Même test pour l'hivernage
        self.warehouse_2.is_winter_storage_warehouse = True

        warehouse_4 = self.env['stock.warehouse'].create({
            'name': 'Warehouse 4',
            'code': 'WH4',
            'company_id': self.company_2.id,
        })
        warehouse_4.is_winter_storage_warehouse = True

        self.assertTrue(self.warehouse_2.is_winter_storage_warehouse)
        self.assertTrue(warehouse_4.is_winter_storage_warehouse)

    @mute_logger('odoo.sql_db')
    def test_sql_constraint_main_rental_warehouse(self):
        """Test SQL constraint for unique main rental warehouse."""
        self.warehouse_1.is_main_rental_warehouse = True

        # Tenter de contourner la contrainte Python en utilisant SQL directement
        with self.assertRaises(IntegrityError):
            self.env.cr.execute("""
                UPDATE stock_warehouse
                SET is_main_rental_warehouse = true
                WHERE id = %s
            """, (self.warehouse_2.id,))
            self.env.cr.commit()

    @mute_logger('odoo.sql_db')
    def test_sql_constraint_winter_storage_warehouse(self):
        """Test SQL constraint for unique winter storage warehouse."""
        self.warehouse_1.is_winter_storage_warehouse = True

        # Tenter de contourner la contrainte Python en utilisant SQL directement
        with self.assertRaises(IntegrityError):
            self.env.cr.execute("""
                UPDATE stock_warehouse
                SET is_winter_storage_warehouse = true
                WHERE id = %s
            """, (self.warehouse_2.id,))
            self.env.cr.commit()

    def test_get_main_rental_warehouse_with_company_id(self):
        """Test getting main rental warehouse for specific company."""
        self.warehouse_1.is_main_rental_warehouse = True
        self.warehouse_3.is_main_rental_warehouse = True

        main_warehouse_company_1 = self.env['stock.warehouse'].get_main_rental_warehouse(
            company_id=self.company_1.id
        )
        main_warehouse_company_2 = self.env['stock.warehouse'].get_main_rental_warehouse(
            company_id=self.company_2.id
        )

        self.assertEqual(main_warehouse_company_1, self.warehouse_1)
        self.assertEqual(main_warehouse_company_2, self.warehouse_3)

    def test_get_main_rental_warehouse_without_company_id(self):
        """Test getting main rental warehouse for current company."""
        # Correct way to change company context in Odoo 18
        self.warehouse_1.is_main_rental_warehouse = True

        # Utilise with_company au lieu de modifier self.env
        warehouse_env = self.env['stock.warehouse'].with_company(self.company_1.id)
        main_warehouse = warehouse_env.get_main_rental_warehouse()

        self.assertEqual(main_warehouse, self.warehouse_1)


    def test_get_winter_storage_warehouse_with_company_id(self):
        """Test getting winter storage warehouse for specific company."""
        self.warehouse_1.is_winter_storage_warehouse = True
        self.warehouse_3.is_winter_storage_warehouse = True

        winter_warehouse_company_1 = self.env['stock.warehouse'].get_winter_storage_warehouse(
            company_id=self.company_1.id
        )
        winter_warehouse_company_2 = self.env['stock.warehouse'].get_winter_storage_warehouse(
            company_id=self.company_2.id
        )

        self.assertEqual(winter_warehouse_company_1, self.warehouse_1)
        self.assertEqual(winter_warehouse_company_2, self.warehouse_3)

    def test_get_winter_storage_warehouse_without_company_id(self):
        """Test getting winter storage warehouse without company_id parameter."""
        # Utilise warehouse_3 qui appartient à company_2
        self.warehouse_3.is_winter_storage_warehouse = True

        # Test: la méthode utilise automatiquement self.env.company
        winter_warehouse = self.env['stock.warehouse'].with_company(self.company_2).get_winter_storage_warehouse()
        self.assertEqual(winter_warehouse, self.warehouse_3)


    def test_get_main_rental_warehouse_none_exists(self):
        """Test getting main rental warehouse when none exists."""
        main_warehouse = self.env['stock.warehouse'].get_main_rental_warehouse(
            company_id=self.company_1.id
        )

        self.assertFalse(main_warehouse)

    def test_get_winter_storage_warehouse_none_exists(self):
        """Test getting winter storage warehouse when none exists."""
        winter_warehouse = self.env['stock.warehouse'].get_winter_storage_warehouse(
            company_id=self.company_1.id
        )

        self.assertFalse(winter_warehouse)

    def test_unset_main_rental_warehouse(self):
        """Test unsetting main rental warehouse."""
        self.warehouse_1.is_main_rental_warehouse = True
        self.assertTrue(self.warehouse_1.is_main_rental_warehouse)

        self.warehouse_1.is_main_rental_warehouse = False
        self.assertFalse(self.warehouse_1.is_main_rental_warehouse)

        # Maintenant un autre entrepôt peut être défini comme principal
        self.warehouse_2.is_main_rental_warehouse = True
        self.assertTrue(self.warehouse_2.is_main_rental_warehouse)

    def test_unset_winter_storage_warehouse(self):
        """Test unsetting winter storage warehouse."""
        with mute_logger('odoo.sql_db'):
            self.warehouse_1.is_winter_storage_warehouse = True
            self.assertTrue(self.warehouse_1.is_winter_storage_warehouse)

            self.warehouse_1.is_winter_storage_warehouse = False
            self.assertFalse(self.warehouse_1.is_winter_storage_warehouse)

            # Maintenant un autre entrepôt peut être défini comme hivernage
            self.warehouse_2.is_winter_storage_warehouse = True
            self.assertTrue(self.warehouse_2.is_winter_storage_warehouse)

    def test_constraint_on_warehouse_update(self):
        """Test constraints when updating existing warehouses."""
        self.warehouse_1.is_main_rental_warehouse = True

        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                self.warehouse_2.write({
                    'is_main_rental_warehouse': True,
                    'name': 'Updated Warehouse 2'
                })


    def test_batch_write_constraint(self):
        """Test constraints when writing to multiple records."""
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                warehouses = self.warehouse_1 | self.warehouse_2
                warehouses.write({'is_main_rental_warehouse': True})

