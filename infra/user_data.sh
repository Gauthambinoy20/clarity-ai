#!/bin/bash
# First-boot setup: docker + compose from the Ubuntu 24.04 repos, and the
# directory the CD workflow deploys into. Everything else (compose file,
# Caddyfile, images) arrives via the deploy workflow, so the instance
# stays cattle, not a pet.
set -euo pipefail

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io docker-compose-v2

systemctl enable --now docker
usermod -aG docker ubuntu

mkdir -p /opt/clarityai
chown ubuntu:ubuntu /opt/clarityai
