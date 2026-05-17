#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Run the docker command
# We use -v $(pwd):/workspace:ro to allow the container to access the current directory
docker compose -f "$SCRIPT_DIR/docker-compose.yml" run --rm -v "$(pwd):/workspace:ro" ask "$@"
