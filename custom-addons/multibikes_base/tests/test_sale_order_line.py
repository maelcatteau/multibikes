from odoo.tests import tagged
from .common import MultibikesBaseTestCommon


@tagged("post_install", "-at_install")
class TestSaleOrderLine(MultibikesBaseTestCommon):
    """Tests pour le modèle SaleOrderLine - MANQUANT !"""

    def test_compute_mb_subtotal(self):
        """Test du calcul automatique de la caution totale"""
        product_variant = self.product.product_variant_id

        line = self.env["sale.order.line"].create({
            "order_id": self.sale_order.id,
            "product_id": product_variant.id,
            "product_uom_qty": 3,  # Quantité multiple
            "price_unit": 50.0,
        })

        # Test du calcul automatique
        expected_caution = 200.0 * 3  # caution unitaire * quantité
        self.assertEqual(line.mb_caution_subtotal, expected_caution)

    def test_caution_subtotal_with_zero_quantity(self):
        """Test avec quantité nulle"""
        product_variant = self.product.product_variant_id

        line = self.env["sale.order.line"].create({
            "order_id": self.sale_order.id,
            "product_id": product_variant.id,
            "product_uom_qty": 0,
            "price_unit": 50.0,
        })

        self.assertEqual(line.mb_caution_subtotal, 0.0)

    def test_related_fields_synchronization(self):
        """Test de la synchronisation des champs reliés"""
        product_variant = self.product.product_variant_id

        line = self.env["sale.order.line"].create({
            "order_id": self.sale_order.id,
            "product_id": product_variant.id,
            "product_uom_qty": 1,
        })

        # Vérification des champs reliés
        self.assertEqual(line.mb_caution_unit, 200.0)
        self.assertEqual(line.mb_value_in_case_of_theft, 500.0)

        # Modification du produit et vérification de la synchronisation
        self.product.mb_caution = 250.0
        line.invalidate_recordset(['mb_caution_unit'])  # Force le recalcul
        self.assertEqual(line.mb_caution_unit, 250.0)