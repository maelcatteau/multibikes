#!/usr/bin/env nu

use config.nu MODULES
use docker-functions.nu *

# Fonction helper pour exécuter des actions sur les modules
def execute_module_action [environment: string, module: string, database: string, action: string] {
    let module_name = ($MODULES | get $module)

    # Construction du script Python par concaténation
    let python_script = ([
        "env['ir.module.module'].search([('name', '=', '"
        $module_name
        "')]).button_immediate_"
        $action
        "()"
    ] | str join "")

    # Utiliser printf qui gère mieux les échappements
    let script_creation = $"printf '%s\\n' \"($python_script)\" > /tmp/($action)_module.py"
    let odoo_command = $"($script_creation) && python3 /usr/bin/odoo shell -d ($database) < /tmp/($action)_module.py && rm /tmp/($action)_module.py"

    connect $environment odoo $odoo_command
}

export def update [...args] {
    let environment = $args | get 0
    let module = $args | get 1
    let database = $args | get 2

    # validations
    if ($args | length) < 3 {
        error make {msg: "Usage: update <env> <module> <database>"}
    }

    execute_module_action $environment $module $database "upgrade"
}

export def uninstall [...args] {
    let environment = $args | get 0
    let module = $args | get 1
    let database = $args | get 2

    # validations
    if ($args | length) < 3 {
        error make {msg: "Usage: uninstall <env> <module> <database>"}
    }

    execute_module_action $environment $module $database "uninstall"
}
