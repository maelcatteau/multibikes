#!/usr/bin/env nu

use config.nu CONTAINERS

# Se connecter au container
export def connect [environment: string, service?: string] {
    let service_name = if $service == null { "odoo" } else { $service }

    try {
        let container_name = ($CONTAINERS | get $environment | get $service_name)

        match $service_name {
            "odoo" => {
                print $"🔗 Connecting to Odoo ($container_name)..."
                docker exec -it $container_name bash
            }
            "db" => {
                print $"🗄️ Connecting to Database ($container_name)..."
                # Se connecter directement à PostgreSQL
                docker exec -it $container_name psql -U odoo -d multibikes
            }
            _ => {
                print $"❌ Unknown service: ($service_name). Available: odoo, db"
            }
        }
    } catch {
        print $"❌ Container not found or environment/service invalid"
        print "Available: dev/staging/prod + odoo/db"
    }
}

# Arrêter la stack
# 🛑 Stop Docker Compose stack
#
# This command stops all services defined in the docker-compose file
# for the specified environment. Use --volumes to also remove named volumes
# which will delete persistent data.
def down [
    environment: string,    # Target environment (dev, staging, prod)
    --volumes (-v)         # Also remove named volumes (WARNING: deletes data!)
] {
    let compose_file = $"docker-compose_($environment).yaml"
    print $"🛑 Stopping ($environment) stack..."
    cd /home/ngner/multibikes/odoo-deployment/
    if $volumes {
        print "⚠️  Also removing volumes..."
        docker compose -f $compose_file down --volumes
    } else {
        docker compose -f $compose_file down
    }
    print $"✅ ($environment) stack stopped!"
}


# Démarrer la stack
export def up [environment: string] {
    let compose_file = $"docker-compose_($environment).yaml"
    print $"🚀 Starting ($environment) stack..."
    cd /home/ngner/multibikes/odoo-deployment/
    docker compose -f $compose_file up -d
    print $"✅ ($environment) stack started!"
}

# Redémarrer la stack
export def restart [environment: string] {
    print $"🔄 Restarting ($environment) stack..."
    down $environment
    sleep 2sec  # Petite pause entre le down et le up
    up $environment
    print $"🎉 ($environment) stack restarted!"
}

export def build [target?: string] {
    cd /home/ngner/multibikes/odoo-deployment/

    match $target {
        "prod" => {
            print "🔨 Building prod image..."
            docker compose -f docker-compose_prod.yaml build
            print "✅ Prod image built!"
        }
        "dev" => {
            print "🔨 Building dev image..."
            docker compose -f docker-compose_dev.yaml build
            print "✅ dev image built!"
        }
        "staging" => {
            print "🔨 Building staging image..."
            docker compose -f docker-compose_staging.yaml build
            print "✅ Staging image built!"
        }
        "base" => {
            print "🔨 Building base image..."
            docker compose -f docker-compose_base.yaml build
            print "✅ Base image built!"
        }
        "test" => {
            print "🧪 Building test image..."
            docker compose -f docker-compose_test.yaml build
            print "✅ Test image built!"
        }
        "all" => {
            print "🔨 Building all images (base + test)..."
            docker compose -f docker-compose_base.yaml build
            docker compose -f docker-compose_test.yaml build
            print "✅ All images built!"
        }
        null => {
            print "❌ Please specify target: base, test, or all"
            print "Examples:"
            print "  ./mb-cli.nu build base"
            print "  ./mb-cli.nu build test"
            print "  ./mb-cli.nu build all"
        }
        _ => {
            print $"❌ Unknown build target: ($target)"
            print "Available targets: base, test, all"
        }
    }
}

export def status [environment: string] {
    print $"📊 Status of ($environment) containers:"
    docker ps --filter $"name=($environment)" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
}

# Afficher les logs
export def logs [environment: string, service?: string] {
    if $service == null {
        # Afficher tous les containers de l'environnement
        let env_containers = ($CONTAINERS | get $environment | values)
        print $"📜 All logs for ($environment) environment:"
        $env_containers | each { |container|
            print $"--- ($container) ---"
            try {
                docker logs --tail=50 $container
            } catch {
                print $"❌ Container ($container) not found or not running"
            }
        }
    } else {
        # Afficher un service spécifique
        let container_name = ($CONTAINERS | get $environment | get $service)
        print $"📜 Logs for ($service) in ($environment): ($container_name)"
        try {
            docker logs --tail=200 -f $container_name
        } catch {
            print $"❌ Container ($container_name) not found or not running"
        }
    }
}