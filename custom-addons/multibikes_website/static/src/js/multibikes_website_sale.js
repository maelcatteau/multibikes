/* FORCE REFRESH: 2025-06-06 20:30 */
/** @odoo-module **/

import { WebsiteSale } from '@website_sale/js/website_sale';
import { _t } from "@web/core/l10n/translation";
import {
    deserializeDateTime,
    formatDate,
    formatDateTime,
} from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
import wSaleUtils from "@website_sale/js/website_sale_utils";
const { DateTime, Duration } = luxon; // S'assurer que Luxon est disponible

WebsiteSale.include({
    events: Object.assign(WebsiteSale.prototype.events || {}, {
        'renting_constraints_loaded': '_onRentingPeriodsLoaded',
    }),

    /**
     * Initialisation pour s'assurer que les propriétés existent.
     */
    init() {
        this._super.apply(this, arguments);
        this.rentingPeriods = null;
        this.websiteTz = 'UTC';
        this.dailyConfigs = {}; // Configuration horaire de la période active
        this.activeRentingPeriod = null; // Pour stocker la période actuellement appliquée
    },

    /**
     * Surcharge de onChangeCombination.
     */
    _onChangeCombination: async function (ev, $parent, combination) {
        // Laisser Odoo gérer ses appels RPC et mettre à jour les infos de base du produit/variante
        const result = await this._super.apply(this, arguments);

        // Mettre à jour les contraintes en fonction de la période de location.
        // Ceci va lire la date sélectionnée, trouver la période, mettre à jour this.*, et déclencher la re-validation.
        if (this.rentingPeriods) {
            this._updateRentalConstraints($parent);
        }

        return result;
    },

    /**
     * Met à jour this.rentingPeriods et this.websiteTz depuis l'événement.
     */
    _onRentingPeriodsLoaded(_event, info) {
        this.rentingPeriods = info.rentingPeriods;
    },

    /**
     * Surcharge pour gérer les contraintes.
     */
    _onRentingConstraintsChanged(_event, info) {
        // console.log("[WebsiteSale] _onRentingConstraintsChanged CALLED with info:", info);

        // Propriétés générales du produit
        if (info.rentingAvailabilities) {
            this.rentingAvailabilities = info.rentingAvailabilities;
        }
        if (info.preparationTime !== undefined) {
            this.preparationTime = info.preparationTime;
        }

        // Si l'événement est déclenché par notre _updateRentalConstraints, les valeurs
        // this.rentingUnavailabilityDays, this.rentingMinimalTime, this.dailyConfigs
        // sont DÉJÀ À JOUR avec les infos de la PÉRIODE.
        // L'événement sert à dire à Odoo de REVALIDER.

        // Important: NE PAS appeler this._super() ici pour un contrôle total.
        // Le framework de location d'Odoo écoute cet événement et va lancer la re-validation
        // de la date/heure, ce qui appellera _getInvalidMessage.
    },

    /**
     * Génère un objet des jours d'indisponibilité à partir de la configuration des jours.
     * @param {Object} dayConfigs Exemple: { "1": {is_open: true, pickup:{allowed:true}, return:{allowed:true}}, ...}
     * @returns {Object} {1: false, 2: true, ...} (Luxon weekday: 1=lundi, true=indisponible)
     */
    _generateUnavailabilityDays: function (dayConfigs) {
        const unavailabilityDays = {};
        if (!dayConfigs || Object.keys(dayConfigs).length === 0) {
            // Si pas de config spécifique, on peut considérer tous les jours comme potentiellement indisponibles

            for (let day = 1; day <= 7; day++) {
                unavailabilityDays[day] = true; // Par défaut, indisponible.
            }
            return unavailabilityDays;
        }

        for (let day = 1; day <= 7; day++) { // Luxon: 1 (Lundi) à 7 (Dimanche)
            const dayKey = day.toString();
            const config = dayConfigs[dayKey];

            // Un jour est globalement indisponible si :
            // 1. Il n'a pas de config OU (sauf si on veut que ce soit "ouvert par défaut")
            // 2. Il est marqué 'is_open: false' OU
            // 3. Ni pickup ni return ne sont autorisés pour ce jour.
            const isUnavailable = !config ||
                !config.is_open ||
                (!config.pickup?.allowed && !config.return?.allowed);
            unavailabilityDays[day] = isUnavailable;
        }
        console.log('[WebsiteSale] Jours d\'indisponibilité générés à partir de dailyConfigs (generateuna):', unavailabilityDays);
        return unavailabilityDays;
    },

    /**
     * Méthode pour mettre à jour les contraintes de locations en
     * fonction de la date de début de la location. En déclenchant
     * un événement renting_constraints_changed sur le document.
     *
     * @private
     * @param {JQueryElement} $parent - Élément parent du formulaire
     * @param {DateTime} [luxonDate] - Date Luxon spécifique à utiliser (optionnel)
     * @returns {boolean} True si les contraintes ont été mises à jour, false sinon
     */
    _updateRentalConstraints: function ($parent, luxonDate) {
        console.log('[WebsiteSale] _updateRentalConstraints appelé');

        let startDate;

        // Utiliser la date Luxon fournie ou récupérer celle du parent
        if (luxonDate && luxonDate.isLuxonDateTime) {
            startDate = luxonDate;
        } else {
            const rentingDates = this._getRentingDates();
            startDate = rentingDates.start_date;
        }

        console.log('[WebsiteSale] Données initiales:', {
            startDate: startDate ? (startDate.isLuxonDateTime ? startDate.toISO() : startDate) : 'non défini',
        });

        if (!this.rentingPeriods) {
            console.warn("[WebsiteSale] Impossible de mettre à jour les contraintes : données non chargées");
            return false;
        }

        // Convertir en objet Date JavaScript pour le traitement
        let dateToCheck;
        if (!startDate) {
            dateToCheck = new Date();
        } else if (startDate.isLuxonDateTime) {
            // Objet DateTime Luxon
            dateToCheck = startDate.toJSDate();
        } else if (typeof startDate === 'string') {
            dateToCheck = new Date(startDate);
        } else if (startDate instanceof Date) {
            dateToCheck = startDate;
        } else {
            dateToCheck = new Date(startDate);
        }

        console.log('[WebsiteSale] Date à vérifier:', dateToCheck);

        // Formater la date en YYYY-MM-DD pour la comparaison avec les périodes
        const formattedDate = dateToCheck.toISOString().split('T')[0];
        console.log('[WebsiteSale] Date formatée pour comparaison:', formattedDate);

        // Trouver la période correspondant à la date
        const matchingPeriod = this.rentingPeriods.find(period => {
            return period.start_date <= formattedDate && period.end_date >= formattedDate;
        });

        console.log('[WebsiteSale] Période correspondante:', matchingPeriod);

        if (!matchingPeriod) {
            console.warn(`[WebsiteSale] Aucune période trouvée pour la date ${formattedDate}`);
            // Utiliser les contraintes par défaut si aucune période ne correspond
            return false;
        }

        // Obtenir le jour de la semaine (0-6, dimanche = 0 en JavaScript)
        const dayOfWeek = dateToCheck.getDay();
        // Ajuster pour avoir lundi = 0, dimanche = 6 (format Odoo)
        const luxonDoW = ((dayOfWeek + 6) % 7) + 1;

        console.log('[WebsiteSale] Jour de la semaine (format luxon):', luxonDoW);

        // Obtenir la configuration du jour pour cette période
        const dayConfig = matchingPeriod.day_configs[luxonDoW];

        console.log('[WebsiteSale] Configuration du jour:', dayConfig);

        const rentingUnavailabilityDays = this._generateUnavailabilityDays(matchingPeriod.day_configs);

        this.rentingUnavailabilityDays = rentingUnavailabilityDays;
        this.rentingMinimalTime = matchingPeriod.minimal_time;
        this.websiteTz = matchingPeriod.websiteTz;
        this.dailyConfigs = matchingPeriod.day_configs;

        const eventData = {
            rentingUnavailabilityDays: rentingUnavailabilityDays,
            rentingMinimalTime: {
                duration: matchingPeriod.minimal_time_duration,
                unit: matchingPeriod.minimal_time_unit,
                name: matchingPeriod.minimal_time_name,
                start_date: matchingPeriod.start_date,
                end_date: matchingPeriod.end_date
            },
            websiteTz: this.websiteTz,
            dailyConfigs: matchingPeriod.day_configs
        };

        console.log('[WebsiteSale] Déclenchement événement renting_constraints_changed avec:', eventData);

        // Déclencher l'événement DOM
        $('.oe_website_sale').trigger('renting_constraints_changed', eventData);

        return true;
    },

    /**
     * Vérifie si l'heure donnée est valide selon this.dailyConfigs.
     * @returns {Object|null} - Objet avec les infos du créneau si valide, null si invalide v22
     */
    _isValidTime: function (dateTimeToCheck, type = 'pickup') {
        console.log('[WebsiteSale] _isValidTime - dateTimeToCheck:', dateTimeToCheck);

        // Vérification préliminaire
        if (!dateTimeToCheck || !dateTimeToCheck.isValid) {
            return { valid: false, reason: 'invalid_date' };
        }

        // Mettre à jour les contraintes seulement si dailyConfigs n'est pas défini
        if (!this.dailyConfigs || Object.keys(this.dailyConfigs).length === 0) {
            console.log('[WebsiteSale] _isValidTime: dailyConfigs manquant, mise à jour des contraintes');
            const constraintsUpdated = this._updateRentalConstraints(null, dateTimeToCheck);

            if (!constraintsUpdated) {
                console.warn('[WebsiteSale] _isValidTime: Impossible de mettre à jour les contraintes');
                return { valid: false, reason: 'constraints_update_failed' };
            }
        } else {
            console.log('[WebsiteSale] _isValidTime: dailyConfigs déjà défini, pas de mise à jour nécessaire');
        }

        // Vérification finale au cas où
        if (!this.dailyConfigs || Object.keys(this.dailyConfigs).length === 0) {
            console.warn("[WebsiteSale] _isValidTime: dailyConfigs toujours manquant après mise à jour.");
            return { valid: false, reason: 'no_config' };
        }

        const dayOfWeek = dateTimeToCheck.weekday;
        const dayConfig = this.dailyConfigs[dayOfWeek.toString()];

        // Vérifier si le jour est ouvert
        if (!dayConfig || !dayConfig.is_open) {
            return {
                valid: false,
                reason: 'day_closed',
                dayOfWeek: dayOfWeek,
                dayName: dateTimeToCheck.toFormat('cccc')
            };
        }

        // Vérifier si le type d'opération est autorisé ce jour-là
        const slotConfig = dayConfig[type];
        if (!slotConfig || !slotConfig.allowed) {
            return {
                valid: false,
                reason: 'operation_not_allowed',
                dayOfWeek: dayOfWeek,
                dayName: dateTimeToCheck.toFormat('cccc'),
                type: type
            };
        }

        // Convertir l'heure de dateTimeToCheck en format décimal
        const timeDecimal = dateTimeToCheck.hour + (dateTimeToCheck.minute / 60);
        const hourFrom = slotConfig.hour_from;
        const hourTo = slotConfig.hour_to;

        // Vérifier si l'heure est dans la plage autorisée
        if (timeDecimal < hourFrom || timeDecimal > hourTo) {
            return {
                valid: false,
                reason: 'outside_hours',
                requestedTime: timeDecimal,
                hourFrom: hourFrom,
                hourTo: hourTo,
                type: type,
                dayName: dateTimeToCheck.toFormat('cccc'),
                formattedHourFrom: this._formatDecimalHour(hourFrom),
                formattedHourTo: this._formatDecimalHour(hourTo)
            };
        }

        // Tout est valide
        return {
            valid: true,
            hourFrom: hourFrom,
            hourTo: hourTo,
            type: type,
            dayName: dateTimeToCheck.toFormat('cccc'),
            formattedHourFrom: this._formatDecimalHour(hourFrom),
            formattedHourTo: this._formatDecimalHour(hourTo)
        };
    },


    /**
     * Convertit une heure décimale en format lisible (ex: 9.75 -> "9h45")
     */
    _formatDecimalHour: function (decimalHour) {
        const hours = Math.floor(decimalHour);
        const minutes = Math.round((decimalHour - hours) * 60);
        return `${hours}h${minutes.toString().padStart(2, '0')}`;
    },

    /**
     * Récupère le message d'erreur de validation pour les dates de location.
     * C'EST CETTE FONCTION QUI EST APPELÉE PAR ODOO POUR LA VALIDATION.
     * Elle doit utiliser les `this.rentingUnavailabilityDays`, `this.rentingMinimalTime` et `this.dailyConfigs`
     * qui ont été mis à jour par `_updateRentalConstraints`.
     */
    _getInvalidMessage: function (startDate, endDate, productId = False) {
        console.log("[WebsiteSale] _getInvalidMessage appelé avec:", {
            startDate: startDate,
            endDate: endDate,
            rentingUnavailabilityDays: this.rentingUnavailabilityDays,
            rentingMinimalTime: this.rentingMinimalTime,
            dailyConfigs: this.dailyConfigs,
        });

        let message = "";

        if (startDate && endDate) {
            // Mettre à jour les contraintes avec la date de début pour s'assurer d'avoir les bonnes données
            this._updateRentalConstraints(null, startDate);

            // 1. Validation jours de la semaine
            if (this.rentingUnavailabilityDays && this.rentingUnavailabilityDays[startDate.weekday]) {
                message = _t("You cannot pick up your rental on that day of the week.");
            } else if (this.rentingUnavailabilityDays && this.rentingUnavailabilityDays[endDate.weekday]) {
                message = _t("You cannot return your rental on that day of the week.");
            }
            // 2. VALIDATION HORAIRE
            else {
                const pickupValidation = this._isValidTime(startDate, 'pickup');
                if (!pickupValidation.valid) {
                    message = this._formatTimeValidationMessage(pickupValidation, 'pickup');
                } else {
                    const returnValidation = this._isValidTime(endDate, 'return');
                    if (!returnValidation.valid) {
                        message = this._formatTimeValidationMessage(returnValidation, 'return');
                    }
                    // 3. AUTRES VALIDATIONS DE DATE
                    else {
                        const rentingDuration = endDate.diff(startDate);
                        if (rentingDuration.as('milliseconds') < 0) {
                            message = _t("The return date should be after the pickup date.");
                        } else if (startDate.startOf("day") < DateTime.now().setZone(this.websiteTz).startOf("day")) {
                            message = _t("The pickup date cannot be in the past.");
                        } else if (!this._isRentalDurationValid(rentingDuration)) {
                            const minimalReq = this.rentingMinimalTime;
                            const formattedMinimalDuration = minimalReq.name || `${minimalReq.duration} ${minimalReq.unit}(s)`;
                            message = _t("The rental duration is too short. The minimum for this period is %s.", formattedMinimalDuration);
                        }
                    }
                }
            }
        } else {
            message = _t("Please select a rental period.");
        }

        return message || this._super.apply(this, arguments);
    },

    /**
     * Vérifie si la durée de location est valide selon les exigences minimales.
     * Version simplifiée pour durées flexibles uniquement.
     */
    _isRentalDurationValid(selectedDuration) {
        const minimalReq = this.rentingMinimalTime;
        if (!minimalReq || !minimalReq.duration) return true;

        const minimalDuration = this._createDurationFromRequirement(minimalReq);

        return selectedDuration >= minimalDuration;
    },

    /**
     * Crée un objet Duration Luxon depuis les exigences minimales
     */
    _createDurationFromRequirement(minimalReq) {
        const unitMap = {
            'hours': 'hours',
            'hour': 'hours',
            'days': 'days',
            'day': 'days',
            'weeks': 'weeks',
            'week': 'weeks',
            'months': 'months',
            'month': 'months'
        };

        const luxonUnit = unitMap[minimalReq.unit] || minimalReq.unit;
        return Duration.fromObject({ [luxonUnit]: minimalReq.duration });
    },


    /**
     * Formate le message d'erreur basé sur la validation horaire
     */
    _formatTimeValidationMessage: function (validation, operationType) {
        const opName = operationType === 'pickup' ? _t('pickup') : _t('return');
        const opNameCap = operationType === 'pickup' ? _t('Pickup') : _t('Return');

        switch (validation.reason) {
            case 'day_closed':
                return _t("The %s day (%s) is closed for rentals.", opName, validation.dayName);

            case 'operation_not_allowed':
                return _t("%s is not allowed on %s.", opNameCap, validation.dayName);

            case 'outside_hours':
                return _t("The %s time is outside allowed hours. %s is allowed on %s from %s to %s.",
                    opName, opNameCap, validation.dayName,
                    validation.formattedHourFrom, validation.formattedHourTo);

            default:
                return _t("The %s time is not valid.", opName);
        }
    },

    async _check_new_dates_on_cart() {
        console.log("[CartValidation] Vérification des nouvelles dates dans le panier");

        // 1. Faire l'appel RPC comme la fonction originale
        const { start_date, end_date, values } = await rpc(
            '/shop/cart/update_renting',
            this._getSerializedRentingDates()
        );

        // 2. Mettre à jour la navbar du panier
        wSaleUtils.updateCartNavBar(values);

        // 3. Convertir les dates reçues du serveur en objets DateTime
        const startDate = deserializeDateTime(start_date, { tz: this.websiteTz });
        const endDate = deserializeDateTime(end_date, { tz: this.websiteTz });

        console.log("[CartValidation] Dates désérialisées:", {
            startDate: startDate,
            endDate: endDate,
            start_date_raw: start_date,
            end_date_raw: end_date
        });

        // 4. S'assurer que les contraintes sont chargées
        if (!this.rentingPeriods) {
            console.log("[CartValidation] Chargement des contraintes de location...");
            try {
                await this._loadRentingConstraints();
            } catch (error) {
                console.error("[CartValidation] Erreur chargement contraintes:", error);
                this._displayCartValidationError(_t("Unable to validate dates"));
                return;
            }
        }

        // 5. Mettre à jour les contraintes avec la date de début
        this._updateRentalConstraints(null, startDate);

        // 6. Validation avec votre système
        const validationMessage = this._getInvalidMessage(startDate, endDate, null);

        if (validationMessage) {
            console.log("[CartValidation] Validation échouée:", validationMessage);
            this._displayCartValidationError(validationMessage);
            // Ne pas mettre à jour les inputs si validation échoue
            return;
        }

        // 7. Si validation OK, mettre à jour les inputs comme la fonction originale
        console.log("[CartValidation] Validation réussie, mise à jour des inputs");
        this._clearCartValidationError();

        const format = this._isDurationWithHours() ? formatDateTime : formatDate;
        document.querySelector("input[name=renting_start_date]").value = format(startDate, { tz: this.websiteTz });
        document.querySelector("input[name=renting_end_date]").value = format(endDate, { tz: this.websiteTz });
    },


    /**
     * Appeler la fonction originale Odoo
     */
    async _originalCheckNewDatesOnCart() {
        const { start_date, end_date, values } = await rpc(
            '/shop/cart/update_renting',
            this._getSerializedRentingDates()
        );
        wSaleUtils.updateCartNavBar(values);
        const format = this._isDurationWithHours() ? formatDateTime : formatDate;
        document.querySelector("input[name=renting_start_date]").value = format(deserializeDateTime(start_date, { tz: this.websiteTz }), { tz: this.websiteTz });
        document.querySelector("input[name=renting_end_date]").value = format(deserializeDateTime(end_date, { tz: this.websiteTz }), { tz: this.websiteTz });
    },

    /**
     * Afficher erreur de validation dans le panier
     */
    _displayCartValidationError(message) {
        // Créer ou mettre à jour le conteneur d'erreur
        let errorContainer = document.querySelector('.cart-validation-error');

        if (!errorContainer) {
            errorContainer = document.createElement('div');
            errorContainer.className = 'cart-validation-error alert alert-danger mt-3';

            // Insérer après le titre du panier ou avant les produits
            const insertPoint = document.querySelector('#cart_products') ||
                document.querySelector('.oe_cart');
            if (insertPoint) {
                insertPoint.insertBefore(errorContainer, insertPoint.firstChild);
            }
        }

        errorContainer.innerHTML = `
            <strong><i class="fa fa-exclamation-triangle"></i> ${_t("Invalid rental period")}</strong><br>
            ${message}
        `;
        errorContainer.classList.remove('d-none');

        // Désactiver le bouton de commande
        this._disableCheckoutButton();

        // Scroll vers l'erreur pour la visibilité
        errorContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
    },

    /**
     * Effacer l'erreur de validation
     */
    _clearCartValidationError() {
        const errorContainer = document.querySelector('.cart-validation-error');
        if (errorContainer) {
            errorContainer.classList.add('d-none');
        }

        this._enableCheckoutButton();
    },

    /**
     * Désactiver le bouton de commande
     */
    _disableCheckoutButton() {
        const checkoutBtn = document.querySelector('a[href*="/shop/checkout"]') ||
            document.querySelector('.btn-checkout') ||
            document.querySelector('#checkout_button');

        if (checkoutBtn) {
            checkoutBtn.style.pointerEvents = 'none';
            checkoutBtn.classList.add('disabled', 'btn-secondary');
            checkoutBtn.classList.remove('btn-primary', 'btn-success');
            checkoutBtn.setAttribute('disabled', 'disabled');

            // Ajouter un tooltip explicatif
            checkoutBtn.title = _t("Please fix the rental period to continue");
        }
    },

    /**
     * Réactiver le bouton de commande
     */
    _enableCheckoutButton() {
        const checkoutBtn = document.querySelector('a[href*="/shop/checkout"]') ||
            document.querySelector('.btn-checkout') ||
            document.querySelector('#checkout_button');

        if (checkoutBtn) {
            checkoutBtn.style.pointerEvents = 'auto';
            checkoutBtn.classList.remove('disabled', 'btn-secondary');
            checkoutBtn.classList.add('btn-primary');
            checkoutBtn.removeAttribute('disabled');
            checkoutBtn.title = '';
        }
    },

});
