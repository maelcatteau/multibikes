# -*- coding: utf-8 -*-

from odoo import models, api
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_availabilities(self, from_date, to_date, warehouse_id, with_cart=False):
        """ Surcharge pour exclure les quantités des entrepôts marqués comme exclus, en tenant compte des transferts internes dans les deux sens et en ajustant les périodes. """
        self.ensure_one()

        _logger.info("Calcul des disponibilités pour le produit %s (ID: %s) de %s à %s", 
                     self.name, self.id, from_date, to_date)
        _logger.info("Entrepôt initial passé : %s", warehouse_id)

        # Si un entrepôt spécifique est demandé, ne pas exclure cet entrepôt même s'il est marqué comme exclu
        if warehouse_id:
            return super(ProductProduct, self)._get_availabilities(
                from_date, to_date, warehouse_id=warehouse_id, with_cart=with_cart
            )

        # Ici, warehouse_id est False : on veut la dispo globale, mais en excluant les entrepôts marqués comme exclus
        # (reste de la logique d'exclusion inchangée)

        # Appel de la méthode d'origine avec tous les entrepôts
        original_availabilities = super(ProductProduct, self)._get_availabilities(
            from_date, to_date, warehouse_id=False, with_cart=with_cart
        )
        _logger.info("Disponibilités initiales (super) : %s", original_availabilities)

        # Récupérer les entrepôts exclus (ceux avec is_excluded_from_availability=True)
        excluded_warehouses = self.env['stock.warehouse'].search([
            ('is_excluded_from_availability', '=', True)
        ])
        _logger.info("Entrepôts exclus trouvés : %s", [(wh.name, wh.id) for wh in excluded_warehouses])

        if not excluded_warehouses:
            return original_availabilities  # Retourner les disponibilités inchangées si aucun entrepôt exclu

        # Récupérer les mouvements de stock sortants depuis les entrepôts exclus
        excluded_warehouse_ids = excluded_warehouses.ids
        outgoing_moves = self.env['stock.move'].search([
            ('product_id', '=', self.id),
            ('state', 'not in', ['done', 'cancel']),  # Mouvements planifiés ou en cours
            ('date', '>=', from_date),
            ('date', '<=', to_date),
            ('location_id.warehouse_id', 'in', excluded_warehouse_ids),  # Sortie d'un entrepôt exclu
            ('location_dest_id.warehouse_id', 'not in', excluded_warehouse_ids),  # Destination hors entrepôt exclu
        ])
        _logger.info("Mouvements sortants depuis entrepôts exclus : %s", 
                     [(move.date, move.product_qty, move.location_id.warehouse_id.name, move.location_dest_id.warehouse_id.name) for move in outgoing_moves])

        # Récupérer les mouvements de stock entrants vers les entrepôts exclus
        incoming_moves = self.env['stock.move'].search([
            ('product_id', '=', self.id),
            ('state', 'not in', ['done', 'cancel']),  # Mouvements planifiés ou en cours
            ('date', '>=', from_date),
            ('date', '<=', to_date),
            ('location_id.warehouse_id', 'not in', excluded_warehouse_ids),  # Origine hors entrepôt exclu
            ('location_dest_id.warehouse_id', 'in', excluded_warehouse_ids),  # Destination dans un entrepôt exclu
        ])
        _logger.info("Mouvements entrants vers entrepôts exclus : %s", 
                     [(move.date, move.product_qty, move.location_id.warehouse_id.name, move.location_dest_id.warehouse_id.name) for move in incoming_moves])

        # Étape 1 : Collecter toutes les dates critiques (début/fin des périodes originales + dates des transferts)
        critical_dates = set()
        for availability in original_availabilities:
            critical_dates.add(availability['start'])
            critical_dates.add(availability['end'])

        for move in outgoing_moves + incoming_moves:
            move_date = move.date if isinstance(move.date, datetime) else datetime.strptime(move.date, '%Y-%m-%d %H:%M:%S')
            critical_dates.add(move_date)

        # Trier les dates critiques pour créer de nouvelles périodes
        critical_dates = sorted(list(critical_dates))
        _logger.info("Dates critiques pour découpage des périodes : %s", critical_dates)

        # Étape 2 : Créer de nouvelles périodes basées sur les dates critiques
        new_periods = []
        for i in range(len(critical_dates) - 1):
            start = critical_dates[i]
            end = critical_dates[i + 1]
            if start >= from_date and end <= to_date and start < end:
                new_periods.append({'start': start, 'end': end})
        _logger.info("Nouvelles périodes créées : %s", new_periods)

        # Étape 3 : Calculer la quantité disponible pour chaque nouvelle période
        adjusted_availabilities = []
        for period in new_periods:
            period_start = period['start']
            period_end = period['end']
            _logger.info("Traitement de la nouvelle période %s à %s", period_start, period_end)

            # Trouver la période originale qui chevauche cette nouvelle période
            base_qty = 0
            for orig_avail in original_availabilities:
                if orig_avail['start'] <= period_start < orig_avail['end'] or \
                   orig_avail['start'] < period_end <= orig_avail['end'] or \
                   (period_start <= orig_avail['start'] and period_end >= orig_avail['end']):
                    base_qty = orig_avail['quantity_available']
                    break
            _logger.info("Quantité de base pour la période (depuis original) : %s", base_qty)

            # Calculer la quantité dans les entrepôts exclus à l'instant T (sans période pour éviter les biais)
            excluded_qty_available = 0
            excluded_qty_in_rent = 0
            for warehouse in excluded_warehouses:
                qty_available = self.with_context(warehouse_id=warehouse.id).qty_available
                qty_in_rent = self.with_context(warehouse_id=warehouse.id).qty_in_rent
                excluded_qty_available += qty_available
                excluded_qty_in_rent += qty_in_rent
                _logger.info("Entrepôt exclu %s (ID: %s) - qty_available: %s, qty_in_rent: %s", 
                             warehouse.name, warehouse.id, qty_available, qty_in_rent)

            # Calculer l'impact cumulatif des transferts jusqu'à la *début* de la période
            # Cela permet de refléter l'état au début de la période
            total_outgoing_qty = 0
            for move in outgoing_moves:
                move_date = move.date if isinstance(move.date, datetime) else datetime.strptime(move.date, '%Y-%m-%d %H:%M:%S')
                if move_date <= period_start:  # Compter uniquement les mouvements avant ou au début de la période
                    total_outgoing_qty += move.product_qty
            _logger.info("Quantité sortante cumulative jusqu'à %s : %s", period_start, total_outgoing_qty)

            total_incoming_qty = 0
            for move in incoming_moves:
                move_date = move.date if isinstance(move.date, datetime) else datetime.strptime(move.date, '%Y-%m-%d %H:%M:%S')
                if move_date <= period_start:  # Compter uniquement les mouvements avant ou au début de la période
                    total_incoming_qty += move.product_qty
            _logger.info("Quantité entrante cumulative jusqu'à %s : %s", period_start, total_incoming_qty)

            # Impact net des transferts au début de la période : on soustrait les sortants et ajoute les entrants
            net_transfer_impact = total_incoming_qty - total_outgoing_qty
            _logger.info("Impact net des transferts jusqu'à %s (entrants - sortants) : %s", period_start, net_transfer_impact)

            # Quantité totale à exclure = (quantité disponible + en location) + impact net des transferts
            total_excluded_qty = max(0, (excluded_qty_available + excluded_qty_in_rent) + net_transfer_impact)
            _logger.info("Quantité totale à exclure pour la période : %s", total_excluded_qty)

            # Ajuster la quantité disponible pour cette période
            adjusted_qty = base_qty - total_excluded_qty
            adjusted_availabilities.append({
                'start': period_start,
                'end': period_end,
                'quantity_available': max(0, adjusted_qty),  # S'assurer que la quantité ne devienne pas négative
            })
            _logger.info("Période %s à %s - Quantité initiale: %s, Quantité ajustée: %s", 
                         period_start, period_end, base_qty, max(0, adjusted_qty))

        _logger.info("Disponibilités ajustées finales : %s", adjusted_availabilities)
        return adjusted_availabilities
