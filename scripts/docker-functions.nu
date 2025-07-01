#!/usr/bin/env nu

use config.nu CONTAINERS

# Se connecter au container
export def connect [...args] {
    let environment = $args | get 0?
    let service = $args | get 1?
    let command = $args | skip 2 | str join " "  # Récupère tout le reste comme commande

    # Validation
    if $environment == null {
        error make {msg: "Usage: connect <environment> [service] [command...]"}
    }

    let service_name = if $service == null { "odoo" } else { $service }

    try {
        let container_name = ($CONTAINERS | get $environment | get $service_name)

        match $service_name {
            "odoo" => {
                if ($command | is-empty) {
                    print $"🔗 Connecting to Odoo ($container_name)..."
                    docker exec -it $container_name bash
                } else {
                    print $"🚀 Executing command in Odoo ($container_name): ($command)"
                    docker exec $container_name bash -c $command
                }
            }
            "db" => {
                if ($command | is-empty) {
                    print $"🗄️ Connecting to Database ($container_name)..."
                    docker exec -it $container_name psql -U odoo -d multibikes
                } else {
                    print $"🗄️ Executing SQL in Database ($container_name): ($command)"
                    docker exec $container_name psql -U odoo -d multibikes -c $command
                }
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

export def down [...args] {
    let environment = $args | get 0?
    let volumes = "--volumes" in $args  # Check si --volumes est dans les args

    if $environment == null {
        error make {msg: "Usage: down <environment> [--volumes]"}
    }

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


export def up [...args] {
    let environment = $args | get 0?

    if $environment == null {
        error make {msg: "Usage: up <environment>"}
    }

    let compose_file = $"docker-compose_($environment).yaml"
    print $"🚀 Starting ($environment) stack..."
    cd /home/ngner/multibikes/odoo-deployment/
    docker compose -f $compose_file up -d
    print $"✅ ($environment) stack started!"
}

# Redémarrer la stack
export def restart [...args] {
    let environment = $args | get 0?

    if $environment == null {
        error make {msg: "Usage: restart <environment>"}
    }

    print $"🔄 Restarting ($environment) stack..."
    down $environment
    sleep 2sec  # Petite pause entre le down et le up
    up $environment
    print $"🎉 ($environment) stack restarted!"
}


export def build [...args] {
    let target = $args | get 0?

    if $target == null {
        print "❌ Please specify target: prod, staging, base, test, or all"
        print "Examples:"
        print "  ./mb-cli.nu build base"
        print "  ./mb-cli.nu build test"
        print "  ./mb-cli.nu build all"
        return
    }

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
            print "✅ Dev image built!"
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
        _ => {
            print $"❌ Unknown build target: ($target)"
            print "Available targets: prod, dev, staging, base, test, all"
        }
    }
}


export def status [...args] {
    let environment = $args | get 0?

    if $environment == null {
        error make {msg: "Usage: status <environment>"}
    }

    print $"📊 Status of ($environment) containers:"
    docker ps --filter $"name=($environment)" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
}


# Afficher les logs
export def logs [...args] {
    let environment = $args | get 0?
    let service = $args | get 1?

    if $environment == null {
        error make {msg: "Usage: logs <environment> [service]"}
    }

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