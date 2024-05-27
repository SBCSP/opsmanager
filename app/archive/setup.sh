#!/bin/bash

echo "Setting up Database and OpsManager"

# Start up the Docker containers
docker compose up -d

# Wait for 20 seconds to allow for containers to start
sleep 20

# Prompt the user for confirmation to proceed with Flask database migrations
read -p "Do you want to run Flask database migrations? (yes/no) " response

case "$response" in 
    [yY][eE][sS]|[yY]) 
        echo "Running Flask database migrations..."
        docker exec -it opsmanager_app flask db init
        docker exec -it opsmanager_app flask db migrate
        docker exec -it opsmanager_app flask db upgrade
        ;;
    [nN][oO]|[nN]) 
        echo "Skipping Flask database migrations."
        ;;
    *)
        echo "Invalid input. Please answer 'yes' or 'no'."
        exit 1
        ;;
esac

echo "Setup complete."