#!/usr/bin/env nu

# Imports de tous les modules
use docker-functions.nu *
use odoo-functions.nu *
use db-functions.nu *


# Dispatcher principal - appel direct des fonctions
def main [subcommand?: string, ...args] {
    match $subcommand {
        # Appels directs - pas de wrappers !
        "connect" => { connect ...$args }
        "logs" => { logs ...$args }
        "update" => { update ...$args }
        "uninstall" => { uninstall ...$args }
        "backup" => { backup ...$args }
        "list_backups" => { list_backups ...$args }
        "restore" => { restore ...$args }
        "up" => { up ...$args }
        "down" => { down ...$args }
        "restart" => { restart ...$args }
        "status" => { status ...$args }
        "build" => { build ...$args }

        _ => { show-help }
    }
}