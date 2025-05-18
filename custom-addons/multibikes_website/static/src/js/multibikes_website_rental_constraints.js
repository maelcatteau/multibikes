/** @odoo-module **/

import { WebsiteSale } from '@website_sale/js/website_sale';
import { rpc } from "@web/core/network/rpc";

// Surcharge du widget WebsiteSale pour ajouter la logique de contraintes de location
WebsiteSale.include({
    /**
     * Surcharge de _onChangeCombination pour déclencher une requête AJAX vers /rental/product/constraints.
     *
     * @param {Event} ev
     * @param {JQueryElement} $parent
     * @param {Object} combination
     * @returns
     */
    _onChangeCombination: function (ev, $parent, combination) {
        console.log('[WebsiteSale] _onChangeCombination appelé', { 
            combinationId: combination?.product_id || 'non défini',
            parentElement: $parent?.attr('class') || 'non défini'
        });
        const result = this._super.apply(this, arguments);
        this._updateRentalConstraints($parent);
        return result;
    },

    /**
     * Méthode pour déclencher une requête AJAX vers /rental/product/constraints
     * et transmettre les contraintes de location via un événement DOM.
     *
     * @param {JQueryElement} $parent
     * @private
     */
    _updateRentalConstraints: async function ($parent) {
        
        const rentingDates = this._getRentingDates();
        const startDate = rentingDates.start_date;
        const productId = this._getProductId($parent.closest('form'));
        

        if (!startDate || !productId) {
            console.warn("[WebsiteSale] Cannot update rental constraints: missing start date or product ID");
            return;
        }

        // Formater la date pour le backend
        let formattedStartDate;
        try {
            if (startDate && startDate.isLuxonDateTime) {
                // Utiliser l'API Luxon pour obtenir une chaîne ISO
                console.log('[WebsiteSale] Start date is of type luxon datetime:', startDate);
                formattedStartDate = startDate.toISO();
                console.log('[WebsiteSale] Formatted start date:', formattedStartDate);
            } else {
                console.log('[WebsiteSale] Start date is of unknown type:', startDate);
                formattedStartDate = new Date(startDate).toISOString();
                
            }
        } catch (e) {
            console.error("[WebsiteSale] Error formatting start date:", e);
            formattedStartDate = startDate.toString();
        }

        try {
            console.log('[WebsiteSale] Envoi requête RPC avec:', { 
                start_date: formattedStartDate, 
                product_id: productId 
            });
            
            const constraints = await rpc('/rental/product/constraints', {
                start_date: formattedStartDate,
                product_id: productId,
            });
            
            console.log('[WebsiteSale] Réponse RPC reçue:', constraints);

            if (constraints) {
                const eventData = {
                    rentingUnavailabilityDays: constraints.renting_unavailability_days || [],
                    rentingMinimalTime: constraints.renting_minimal_time || { duration: 0, unit: 'day', start_date: null, end_date: null },
                    websiteTz: constraints.website_tz || 'UTC'
                };
                
                // Déclencher l'événement DOM avec la structure exacte du code original
                $('.oe_website_sale').trigger('renting_constraints_changed', eventData);
                console.log('[WebsiteSale] Événement déclenché avec succès, avec les données:', eventData);
            } else {
                console.warn('[WebsiteSale] Aucune contrainte reçue du serveur');
            }
        } catch (error) {
            console.error("[WebsiteSale] Error fetching rental constraints:", error);
        }
    }
});
