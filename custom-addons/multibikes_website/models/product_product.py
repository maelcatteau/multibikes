# -*- coding: utf-8 -*-

from odoo import models, api
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_availabilities(self, from_date, to_date, warehouse_id, with_cart=False):
        """
        Surcharge pour exclure les quantités des entrepôts d'hivernage, 
        en tenant compte des transferts internes dans les deux sens et en ajustant les périodes.
        """
        self.ensure_one()
        
        _logger.info("Calcul des disponibilités pour le produit %s (ID: %s) de %s à %s", 
                     self.name, self.id, from_date, to_date)
        
        # Si un entrepôt spécifique est demandé, pas d'exclusion d'hivernage
        if warehouse_id:
            return super(ProductProduct, self)._get_availabilities(
                from_date, to_date, warehouse_id=warehouse_id, with_cart=with_cart
            )
        
        # Récupérer les entrepôts d'hivernage
        winter_warehouses = self._get_winter_storage_warehouses()
        if not winter_warehouses:
            return super(ProductProduct, self)._get_availabilities(
                from_date, to_date, warehouse_id=False, with_cart=with_cart
            )
        
        # Calculs principaux
        original_availabilities = super(ProductProduct, self)._get_availabilities(
            from_date, to_date, warehouse_id=False, with_cart=with_cart
        )
        
        # Récupérer les mouvements de transfert
        outgoing_moves, incoming_moves = self._get_winter_transfer_moves(
            from_date, to_date, winter_warehouses
        )
        
        # Créer les nouvelles périodes basées sur les dates critiques
        new_periods = self._create_adjusted_periods(
            from_date, to_date, original_availabilities, outgoing_moves, incoming_moves
        )
        
        # Calculer les disponibilités ajustées
        return self._calculate_adjusted_availabilities(
            new_periods, original_availabilities, winter_warehouses,
            outgoing_moves, incoming_moves
        )

    def _get_winter_storage_warehouses(self):
        """Récupère tous les entrepôts d'hivernage."""
        warehouses = self.env['stock.warehouse'].search([
            ('is_winter_storage_warehouse', '=', True)
        ])
        
        _logger.info("Entrepôts d'hivernage trouvés : %s", 
                     [(wh.name, wh.id) for wh in warehouses])
        return warehouses

    def _get_winter_transfer_moves(self, from_date, to_date, winter_warehouses):
        """
        Récupère les mouvements de transfert depuis/vers les entrepôts d'hivernage.
        
        Returns:
            tuple: (outgoing_moves, incoming_moves)
        """
        winter_warehouse_ids = winter_warehouses.ids
        
        # Mouvements sortants depuis les entrepôts d'hivernage
        outgoing_moves = self.env['stock.move'].search([
            ('product_id', '=', self.id),
            ('state', 'not in', ['done', 'cancel']),
            ('date', '>=', from_date),
            ('date', '<=', to_date),
            ('location_id.warehouse_id', 'in', winter_warehouse_ids),
            ('location_dest_id.warehouse_id', 'not in', winter_warehouse_ids),
        ])
        
        # Mouvements entrants vers les entrepôts d'hivernage
        incoming_moves = self.env['stock.move'].search([
            ('product_id', '=', self.id),
            ('state', 'not in', ['done', 'cancel']),
            ('date', '>=', from_date),
            ('date', '<=', to_date),
            ('location_id.warehouse_id', 'not in', winter_warehouse_ids),
            ('location_dest_id.warehouse_id', 'in', winter_warehouse_ids),
        ])
        
        _logger.info("Mouvements sortants depuis entrepôts d'hivernage : %s", len(outgoing_moves))
        _logger.info("Mouvements entrants vers entrepôts d'hivernage : %s", len(incoming_moves))
        
        return outgoing_moves, incoming_moves

    def _create_adjusted_periods(self, from_date, to_date, original_availabilities, 
                               outgoing_moves, incoming_moves):
        """
        Crée les nouvelles périodes basées sur les dates critiques.
        
        Returns:
            list: Liste des périodes avec start/end
        """
        # Collecter toutes les dates critiques
        critical_dates = set()
        
        # Ajouter les dates des périodes originales
        for availability in original_availabilities:
            critical_dates.add(availability['start'])
            critical_dates.add(availability['end'])
        
        # Ajouter les dates des transferts
        for move in outgoing_moves + incoming_moves:
            move_date = move.date if isinstance(move.date, datetime) else \
                       datetime.strptime(move.date, '%Y-%m-%d %H:%M:%S')
            critical_dates.add(move_date)
        
        # Trier et créer les nouvelles périodes
        critical_dates = sorted(list(critical_dates))
        _logger.info("Dates critiques : %s", len(critical_dates))
        
        new_periods = []
        for i in range(len(critical_dates) - 1):
            start = critical_dates[i]
            end = critical_dates[i + 1]
            if start >= from_date and end <= to_date and start < end:
                new_periods.append({'start': start, 'end': end})
        
        _logger.info("Nouvelles périodes créées : %s", len(new_periods))
        return new_periods

    def _calculate_adjusted_availabilities(self, new_periods, original_availabilities,
                                         winter_warehouses, outgoing_moves, incoming_moves):
        """
        Calcule les disponibilités ajustées pour chaque periode.
        
        Returns:
            list: Liste des disponibilités ajustées
        """
        adjusted_availabilities = []
        
        for period in new_periods:
            # Trouver la quantité de base
            base_qty = self._find_base_quantity(period, original_availabilities)
            
            # Calculer les quantités d'hivernage
            winter_qty_total = self._calculate_winter_quantities(winter_warehouses)
            
            # Calculer l'impact des transferts
            net_transfer_impact = self._calculate_transfer_impact(
                period['start'], outgoing_moves, incoming_moves
            )
            
            # Ajuster la quantité
            total_winter_qty = max(0, winter_qty_total + net_transfer_impact)
            adjusted_qty = max(0, base_qty - total_winter_qty)
            
            adjusted_availabilities.append({
                'start': period['start'],
                'end': period['end'],
                'quantity_available': adjusted_qty,
            })
            
            _logger.info("Période %s à %s - Base: %s, Ajustée: %s", 
                        period['start'], period['end'], base_qty, adjusted_qty)
        
        return adjusted_availabilities

    def _find_base_quantity(self, period, original_availabilities):
        """Trouve la quantité de base pour une période donnée."""
        for orig_avail in original_availabilities:
            if (orig_avail['start'] <= period['start'] < orig_avail['end'] or
                orig_avail['start'] < period['end'] <= orig_avail['end'] or
                (period['start'] <= orig_avail['start'] and period['end'] >= orig_avail['end'])):
                return orig_avail['quantity_available']
        return 0

    def _calculate_winter_quantities(self, winter_warehouses):
        """Calcule les quantités totales dans les entrepôts d'hivernage."""
        total_qty = 0
        for warehouse in winter_warehouses:
            qty_available = self.with_context(warehouse_id=warehouse.id).qty_available
            qty_in_rent = self.with_context(warehouse_id=warehouse.id).qty_in_rent
            total_qty += qty_available + qty_in_rent
            
        _logger.info("Quantité totale d'hivernage : %s", total_qty)
        return total_qty

    def _calculate_transfer_impact(self, period_start, outgoing_moves, incoming_moves):
        """Calcule l'impact net des transferts jusqu'au début de la période."""
        total_outgoing = sum(
            move.product_qty for move in outgoing_moves
            if (move.date if isinstance(move.date, datetime) else
                datetime.strptime(move.date, '%Y-%m-%d %H:%M:%S')) <= period_start
        )
        
        total_incoming = sum(
            move.product_qty for move in incoming_moves
            if (move.date if isinstance(move.date, datetime) else
                datetime.strptime(move.date, '%Y-%m-%d %H:%M:%S')) <= period_start
        )
        
        net_impact = total_incoming - total_outgoing
        _logger.info("Impact transferts jusqu'à %s : entrants=%s, sortants=%s, net=%s",
                    period_start, total_incoming, total_outgoing, net_impact)
        
        return net_impact
