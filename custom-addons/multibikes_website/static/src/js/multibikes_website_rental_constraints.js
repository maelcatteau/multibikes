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
            console.warn("Cannot update rental constraints: missing start date or product ID");
            return;
        }

        // Formater la date pour le backend
        let formattedStartDate;
        try {
            if (typeof startDate === 'string') {
                formattedStartDate = startDate;
            } else if (startDate instanceof Date) {
                formattedStartDate = startDate.toISOString();
            } else {
                formattedStartDate = new Date(startDate).toISOString();
            }
        } catch (e) {
            console.error("Error formatting start date:", e);
            formattedStartDate = startDate.toString();
        }

        try {
            const constraints = await rpc('/rental/product/constraints', {
                start_date: formattedStartDate,
                product_id: productId,
            });

            if (constraints) {
                // Déclencher l'événement DOM avec la structure exacte du code original
                $('.oe_website_sale').trigger('renting_constraints_changed', {
                    rentingUnavailabilityDays: constraints.renting_unavailability_days || [],
                    rentingMinimalTime: constraints.renting_minimal_time || { duration: 0, unit: 'day' },
                    websiteTz: constraints.website_tz || 'UTC'
                });
            }
        } catch (error) {
            console.error("Error fetching rental constraints:", error);
        }
    }
});
