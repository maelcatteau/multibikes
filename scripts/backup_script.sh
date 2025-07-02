#!/bin/bash

# Charger l'environnement complet
export HOME=/home/ngner
export PATH=/home/ngner/.vscode-server/cli/servers/Stable-2901c5ac6db8a986a5666c3af51ff804d05af0d4/server/bin/remote-cli:/home/ngner/.local/bin:/home/ngner/.cargo/bin:/usr/local/sbin:/usr/sbin:/sbin:/usr/local/bin:/usr/bin:/bin:/usr/local/games:/usr/games
export SHELL=/bin/bash
export USER=ngner
export LOGNAME=ngner

# Se placer dans le bon répertoire
cd /home/ngner/multibikes/odoo-deployment/scripts

# Lancer la commande
/home/ngner/.cargo/bin/nu -c "source /home/ngner/multibikes/odoo-deployment/scripts/mb-cli/db-functions.nu ; backup prod multibikes --cron"