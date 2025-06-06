# -*- coding: utf-8 -*-

from odoo.tests import tagged
from .common import MultibikesBaseTestCommon


@tagged("post_install", "-at_install")
class TestSaleOrder(MultibikesBaseTestCommon):
    """Tests pour le modèle SaleOrder"""

    def test_caution_fields(self):
        """Test des champs de caution sur la commande"""
        # Vérification des valeurs initiales
        self.assertEqual(self.sale_order.mb_type_de_caution, "carte_bancaire")
        self.assertEqual(self.sale_order.mb_numero_de_caution, 12345)

        # Modification du type de caution et vérification
        self.sale_order.mb_type_de_caution = "cheque"
        self.assertEqual(self.sale_order.mb_type_de_caution, "cheque")

    def test_create_order_with_caution(self):
        """Test de création d'une commande avec caution"""
        new_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "mb_type_de_caution": "espece",
                "mb_numero_de_caution": 54321,
            }
        )

        self.assertEqual(new_order.mb_type_de_caution, "espece")
        self.assertEqual(new_order.mb_numero_de_caution, 54321)

    def test_add_rental_line(self):
        """Test d'ajout d'une ligne de location à une commande"""
        # Création d'un produit variant à partir du template
        product_variant = self.product.product_variant_id

        # Ajout d'une ligne de location à la commande
        self.env["sale.order.line"].create(
            {
                "order_id": self.sale_order.id,
                "product_id": product_variant.id,
                "product_uom_qty": 1,
                "product_uom": product_variant.uom_id.id,
                "price_unit": product_variant.list_price,
                "name": product_variant.name,
                "is_rental": True,
            }
        )

        # Vérification que la ligne a été ajoutée
        self.assertEqual(len(self.sale_order.order_line), 1)
        self.assertTrue(self.sale_order.order_line[0].is_rental)
