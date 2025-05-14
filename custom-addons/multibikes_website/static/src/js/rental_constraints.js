/** @odoo-module **/

import { WebsiteSale } from '@website_sale/js/website_sale';
import { rpc } from "@web/core/network/rpc";
import { parseDateTime } from "@web/core/l10n/dates";

// Surcharge du widget WebsiteSale pour ajouter la logique de contraintes de location
WebsiteSale.include({
    /**
     * Surcharge de _onChangeCombination pour déclencher une requête AJAX vers /rental/product/constraints
     * après la vérification de la période de location.
     *
     * @param {Event} ev
     * @param {JQueryElement} $parent
     * @param {Object} combination
     * @returns
     */
    _onChangeCombination: function (ev, $parent, combination) {
        const result = this._super.apply(this, arguments);
        this._verifyValidRentingPeriod($parent);
        // Ajouter la logique pour récupérer les contraintes de location
        this._updateRentalConstraints($parent);
        return result;
    },

    /**
     * Méthode pour déclencher une requête AJAX vers /rental/product/constraints
     * et mettre à jour les contraintes de location via l'événement renting_constraints_changed.
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
            // Convertir la date en format ISO standard que le backend peut comprendre
            if (typeof startDate === 'string') {
                formattedStartDate = startDate;
            } else if (startDate instanceof Date) {
                formattedStartDate = startDate.toISOString();
            } else {
                // Pour les formats daterangepicker ou autres
                formattedStartDate = new Date(startDate).toISOString();
            }
            console.log("Formatted Start Date for RPC:", formattedStartDate);
        } catch (e) {
            console.error("Error formatting start date:", e);
            // Fallback au format original
            formattedStartDate = startDate.toString();
        }

        console.log("Fetching rental constraints. Start Date:", formattedStartDate, "Product ID:", productId);

        try {
            // Utiliser rpc importé directement
            const constraints = await rpc('/rental/product/constraints', {
                start_date: formattedStartDate,
                product_id: productId,
            });

            console.log("Rental constraints received:", constraints);

            if (constraints) {
                // Forcer la mise à jour de l'interface utilisateur
                this._clearRentingValidationErrors($parent);
                
                // Déclencher l'événement pour mettre à jour le frontend
                this.trigger_up('renting_constraints_changed', {
                    rentingMinimalTime: constraints.renting_minimal_time || 0,
                    rentingUnavailabilityDays: constraints.renting_unavailability_days || [],
                    websiteTz: constraints.website_tz || null
                });
                
                // Vérifier à nouveau la validité de la période de location avec les nouvelles contraintes
                setTimeout(() => {
                    this._verifyValidRentingPeriod($parent);
                }, 100); // Court délai pour s'assurer que les nouvelles contraintes sont appliquées
            }
        } catch (error) {
            console.error("Error fetching rental constraints:", error);
        }
    },
    
    /**
     * Méthode pour effacer les erreurs de validation de location existantes
     * 
     * @param {JQueryElement} $parent
     * @private
     */
    _clearRentingValidationErrors: function ($parent) {
        const $rentingError = $parent.find('.renting_warning');
        if ($rentingError.length) {
            $rentingError.hide();
        }
    }
});
