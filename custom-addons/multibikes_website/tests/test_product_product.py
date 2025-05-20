# -*- coding: utf-8 -*-
from odoo.tests import tagged
from .common import MultibikesWebsiteTestCommon as MultibikesWebsiteProductTestCommon
from datetime import datetime, timedelta

@tagged('post_install', '-at_install')
class TestProductProduct(MultibikesWebsiteProductTestCommon):
    """Tests pour le modèle product.product avec les extensions multibikes_website"""
    
    def setUp(self):
        super().setUp()
        self.start_date = self.start_date_dt
    
    
    def test_get_availabilities(self):
        """Test de la méthode _get_availabilities avec exclusion d'entrepôts"""
        # Convertir les dates en datetime si ce sont des strings
        start_date = self.start_date if isinstance(self.start_date, datetime) else datetime.strptime(self.start_date, '%Y-%m-%d %H:%M:%S')
        end_date = self.end_date if isinstance(self.end_date, datetime) else datetime.strptime(self.end_date, '%Y-%m-%d %H:%M:%S')
        
        # Sans spécifier d'entrepôt (tous les entrepôts)
        availabilities = self.rental_product._get_availabilities(start_date, end_date, False)
        
        # Vérifier que les disponibilités sont ajustées (excluant l'entrepôt marqué comme exclu)
        total_qty_main = 5.0  # Quantité dans l'entrepôt principal
        total_qty_excluded = 3.0  # Quantité dans l'entrepôt exclu
        
        # Vérifier que les périodes générées sont correctes
        self.assertTrue(len(availabilities) > 0, "Des périodes de disponibilité devraient être générées")
        
        # Vérifier que la première période a la bonne quantité disponible
        # On s'attend à ce que les stocks de l'entrepôt exclu soient retirés
        first_period = availabilities[0]
        self.assertEqual(first_period['quantity_available'], total_qty_main, 
                        f"La quantité disponible devrait être {total_qty_main} (uniquement l'entrepôt principal)")
        
        # Vérifier l'effet des mouvements de stock sur les périodes
        # Trouver une période après le mouvement sortant (1 unité de l'exclu vers le principal)
        outgoing_move_date = datetime.strptime(self.outgoing_move.date, '%Y-%m-%d %H:%M:%S')
        
        # Trouver la période qui contient la date du mouvement sortant
        post_outgoing_period = None
        for period in availabilities:
            if period['start'] < outgoing_move_date < period['end'] or \
               (period['start'] > outgoing_move_date and period == availabilities[-1]):
                post_outgoing_period = period
                break
        
        # Si nous avons trouvé une période après le mouvement sortant
        if post_outgoing_period:
            # La quantité disponible devrait être augmentée de 1 (mouvement de l'exclu vers le principal)
            # Mais comme l'entrepôt exclu n'est pas compté, la quantité reste inchangée
            self.assertEqual(post_outgoing_period['quantity_available'], total_qty_main)
        
        # Vérifier avec un entrepôt spécifique
        availabilities_main = self.rental_product._get_availabilities(
            start_date, end_date, self.main_warehouse.id
        )
        
        # La quantité disponible devrait être celle de l'entrepôt principal uniquement
        self.assertEqual(availabilities_main[0]['quantity_available'], total_qty_main)
        
        # Tests avec l'entrepôt exclu
        availabilities_excluded = self.rental_product._get_availabilities(
            start_date, end_date, self.excluded_warehouse.id
        )
        
        # La quantité disponible devrait être celle de l'entrepôt exclu uniquement
        self.assertEqual(availabilities_excluded[0]['quantity_available'], total_qty_excluded)
