#!/usr/bin/env nu

# Dictionnaire global des containers
export const CONTAINERS = {
    dev: {
        odoo: "odoo-dev",
        db: "odoo-deployment-db-dev-1"
    },
    staging: {
        odoo: "odoo-staging",
        db: "odoo-deployment-db-staging-1"
    },
    prod: {
        odoo: "odoo-prod",
        db: "odoo-deployment-db-prod-1"
    }
}
export const MODULES = {
    base: "multibikes_base"
    signature: "multibikes_signature"
    prolongation: "multibikes_prolongation"
    website: "multibikes_website"
    web_sign: "multibikes_web_digital_sign"
}