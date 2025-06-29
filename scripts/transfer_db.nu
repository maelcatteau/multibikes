#!/usr/bin/env -S nu --stdin

# ============================================
# TRANSFER_DB.NU - Version Nushell moderne
# Remplacement progressif de transfer_db.sh
# ============================================

use lib/config.nu [ENVIRONMENTS, COLORS]
use lib/logging.nu [log, error, warning, confirm, confirm-with-text]
use lib/docker.nu [get-container-name, container-exists, container-running]

# Autocomplétion pour les actions
def "nu-complete-actions" [] {
    ["backup", "restore"]
}

# Autocomplétion pour les environnements
def "nu-complete-envs" [] {
    $ENVIRONMENTS | columns
}

# Afficher l'aide (basé sur l'ancien script)
def show-help [] {
    print $"($COLORS.cyan)============================================($COLORS.reset)"
    print $"($COLORS.cyan)  TRANSFER_DB.NU - Gestion des bases Odoo  ($COLORS.reset)"
    print $"($COLORS.cyan)============================================($COLORS.reset)"
    print ""
    print $"($COLORS.yellow)Usage:($COLORS.reset)"
    print "  ./transfer_db.nu <action> <environment> <database> [options]"
    print ""
    print $"($COLORS.yellow)Actions:($COLORS.reset)"
    print "  backup   - Sauvegarder une base de données Odoo"
    print "  restore  - Restaurer une base de données Odoo"
    print ""
    print $"($COLORS.yellow)Environnements disponibles:($COLORS.reset)"
    let envs = ($ENVIRONMENTS | columns | str join ", ")
    print $"  ($envs)"
    print ""
    print $"($COLORS.yellow)Exemples:($COLORS.reset)"
    print "  ./transfer_db.nu backup dev mydb /home/user/backups"
    print "  ./transfer_db.nu restore prod mydb /path/to/mydb.sql"
    print ""
    print $"($COLORS.green)📍 Version Nushell - Phase 2: Validation et structure($COLORS.reset)"
}

# Valider les paramètres d'entrée (Phase 2)
def validate-inputs [
    action: string
    environment: string
    database: string
    file_or_dir: string
] {
    # Valider l'action
    if $action not-in ["backup", "restore"] {
        error $"Action '($action)' invalide. Actions: backup, restore"
    }

    # Valider l'environnement
    if $environment not-in ($ENVIRONMENTS | columns) {
        error $"Environnement '($environment)' invalide. Environnements: ($ENVIRONMENTS | columns | str join ', ')"
    }

    # Valider le nom de base (basique pour l'instant)
    if ($database | str length) < 2 {
        error "Le nom de base de données doit faire au moins 2 caractères"
    }

    # Valider le conteneur
    let container = (get-container-name $environment)
    if not (container-exists $container) {
        error $"Le conteneur ($container) n'existe pas"
    }

    if not (container-running $container) {
        error $"Le conteneur ($container) n'est pas démarré"
    }

    log $"✅ Validation OK - Environnement: ($environment), Base: ($database)"
}

# ============================================
# FONCTIONS DE BACKUP
# ============================================

# Sauvegarder une base de données Odoo
def backup-odoo [
    environment: string@"nu-complete-envs"
    database: string
    backup_dir: string = "/tmp"
] {
    log $"🔄 Starting backup: ($database) from ($environment)"

    # Validation de l'environnement
    if $environment not-in ($ENVIRONMENTS | columns) {
        error $"Invalid environment: ($environment)"
        return
    }

    # Obtenir le conteneur
    let container = (get-container-name $environment)
    log $"📦 Container: ($container)"

    # Vérifier que le conteneur existe et tourne
    if not (container-exists $container) {
        error $"Container ($container) does not exist"
        return
    }

    if not (container-running $container) {
        error $"Container ($container) is not running"
        return
    }

    # Créer le répertoire de backup s'il n'existe pas
    mkdir $backup_dir

    # Générer le nom de fichier avec timestamp
    let timestamp = (date now | format date "%Y%m%d_%H%M%S")
    let backup_filename = $"($database)_($environment)_($timestamp).sql"
    let backup_path = ($backup_dir | path join $backup_filename)

    log $"💾 Backup file: ($backup_path)"

    # Vérifier que la base existe dans le conteneur
    let db_check = (docker-exec $container $"psql -U odoo -d postgres -tAc \"SELECT 1 FROM pg_database WHERE datname='($database)'\"" --quiet)

    if ($db_check | str trim) == "" {
        error $"Database '($database)' not found in ($environment)"
        return
    }

    # Exécuter le backup avec pg_dump
    log $"🚀 Running pg_dump..."
    let dump_command = $"pg_dump -U odoo -d ($database) --verbose --no-owner --no-privileges"

    try {
        docker exec $container bash -c $dump_command | save $backup_path
        log $"✅ Backup completed successfully: ($backup_path)"

        # Afficher les infos du fichier
        let file_size = (ls $backup_path | get size | first)
        log $"📊 File size: ($file_size)"

        return $backup_path
    } catch {
        error $"❌ Backup failed for ($database)"
        return
    }
}
# ============================================
# FONCTIONS DE RESTORE
# ============================================

# Restaurer une base de données Odoo
def restore-odoo [
    environment: string@"nu-complete-envs"
    database: string
    backup_file: string
] {
    log $"🔄 Starting restore: ($backup_file) to ($database) in ($environment)"

    # Validation de l'environnement
    if $environment not-in ($ENVIRONMENTS | columns) {
        error $"Invalid environment: ($environment)"
        return
    }

    # Vérifier que le fichier de backup existe
    if not ($backup_file | path exists) {
        error $"Backup file not found: ($backup_file)"
        return
    }

    # Obtenir le conteneur
    let container = (get-container-name $environment)
    log $"📦 Container: ($container)"

    # Vérifier que le conteneur existe et tourne
    if not (container-exists $container) {
        error $"Container ($container) does not exist"
        return
    }

    if not (container-running $container) {
        error $"Container ($container) is not running"
        return
    }

    # Vérifier si la base existe déjà
    let db_check = (docker-exec $container $"psql -U odoo -d postgres -tAc \"SELECT 1 FROM pg_database WHERE datname='($database)'\"" --quiet)

    if ($db_check | str trim) != "" {
        log $"⚠️  Database '($database)' already exists in ($environment)"
        print $"Do you want to drop and recreate it? (y/N): "
        let response = (input)

        if ($response | str downcase) != "y" {
            log $"❌ Restore cancelled by user"
            return
        }

        # Dropper la base existante
        log $"🗑️  Dropping existing database..."
        docker-exec $container $"dropdb -U odoo ($database)"
    }

    # Créer la nouvelle base
    log $"🏗️  Creating database ($database)..."
    docker-exec $container $"createdb -U odoo ($database)"

    # Copier le fichier de backup dans le conteneur
    let temp_backup = $"/tmp/restore_($database).sql"
    log $"📋 Copying backup file to container..."
    docker cp $backup_file $"($container):($temp_backup)"

    # Restaurer la base
    log $"🚀 Running restore..."
    let restore_command = $"psql -U odoo -d ($database) -f ($temp_backup)"

    try {
        docker-exec $container $restore_command
        log $"✅ Restore completed successfully"

        # Nettoyer le fichier temporaire
        docker-exec $container $"rm -f ($temp_backup)" --quiet

        log $"🎉 Database ($database) restored in ($environment)"
    } catch {
        error $"❌ Restore failed for ($database)"
        # Nettoyer en cas d'erreur
        docker-exec $container $"rm -f ($temp_backup)" --quiet
        return
    }
}

# ============================================
# FONCTIONS UTILITAIRES SUPPLÉMENTAIRES
# ============================================

# Lister les bases de données disponibles
def list-databases [environment: string@"nu-complete-envs"] {
    let container = (get-container-name $environment)

    if not (container-running $container) {
        error $"Container ($container) is not running"
        return
    }

    log $"📋 Databases in ($environment):"
    let databases = (docker-exec $container "psql -U odoo -d postgres -tAc \"SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname\"" --quiet)

    $databases | lines | each {|db| log $"  - ($db)"}
}