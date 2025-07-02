#!/usr/bin/env nu

# mod.nu - Point d'entrée du module mb-cli

# Re-exports de tous les modules (comme vos imports actuels)
export use docker-functions.nu *
export use odoo-functions.nu *
export use db-functions.nu *

# Optionnel : fonction d'aide générale (remplace votre show-help)
export def help [] {
    print "MB CLI - Available commands:"
    print " <> for mandatory parameters"
    print " [] for optionnal parameters"
    print " --flag for optionnal flags"
    print ""
    print "🐳 Docker commands:"
    print "  up <env> --build                                  - Start environment"
    print "  down <env> --volumes                              - Stop environment"
    print "  restart <env> --volumes --build                   - Restart environment"
    print "  status [env]                                      - Show containers status"
    print "  build <env>                                       - Build odoo image"
    print "  logs <env> [service]                              - Show logs"
    print "  connect <env> [service] [<database>] [command]    - Connect to container and execute command"
    print "                                                    (database parameter not needed for odoo service)"
    print ""
    print "🗄️  Database commands:"
    print "  backup <env> <database>                           - Backup database"
    print "  list_backups <env>                                - List available backups"
    print "  list_db <env>                                     - List available databases"
    print "  transfer <source_env> <target_env> <database>     - List available databases"
    print "  restore <env> <file>                              - Restore from backup"
    print ""
    print "📦 Odoo commands:"
    print "  update <env> <modules>    - Update Odoo modules"
    print "  uninstall <env> <modules> - Uninstall modules"
    print ""
    print "Use '<command> --help' for detailed help on each command."
}