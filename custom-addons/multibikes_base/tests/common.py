# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class MultibikesBaseTestCommon(TransactionCase):
    """Classe commune pour les tests du module multibikes_base"""

    @classmethod
    def setUpClass(cls):
        """Configuration initiale des tests"""
        super(MultibikesBaseTestCommon, cls).setUpClass()

        # Création d'un partenaire de test
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Client Test",
                "email": "client.test@example.com",
            }
        )

        # Création d'une catégorie de produit
        cls.product_category = cls.env["product.category"].create(
            {
                "name": "Vélos",
            }
        )

        # Création d'un produit (vélo) de test
        cls.product = cls.env["product.template"].create(
            {
                "name": "Vélo de Test",
                "type": "consu",
                "categ_id": cls.product_category.id,
                "list_price": 50.0,
                "rent_ok": True,
                "mb_caution": 200.0,
                "mb_value_in_case_of_theft": 500.0,
                "mb_size_min": 160.0,
                "mb_size_max": 185.0,
            }
        )

        # Création d'une commande de test
        cls.sale_order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "mb_type_de_caution": "carte_bancaire",
                "mb_numero_de_caution": 12345,
            }
        )

        cls.products = cls.env["product.template"].create([
            {
                "name": f"Vélo {i}",
                "type": "consu",
                "list_price": 50.0 + i * 10,
                "mb_caution": 200.0 + i * 50,
                "mb_value_in_case_of_theft": 500.0 + i * 100,
            } for i in range(5)
        ])


    def test_multiple_products_performance(self):
        """Test de performance avec plusieurs produits"""
        variants = self.products.product_variant_ids

        # Création massive de lignes
        lines_data = [{
            "order_id": self.sale_order.id,
            "product_id": variant.id,
            "product_uom_qty": 2,
            "price_unit": variant.list_price,
        } for variant in variants]

        lines = self.env["sale.order.line"].create(lines_data)

        # Vérification que les calculs sont corrects
        expected_total = sum(line.mb_caution_subtotal for line in lines)
        self.assertEqual(self.sale_order.mb_caution_total, expected_total)