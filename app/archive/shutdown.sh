#!/bin/bash

echo "Shutting down Docker Compose services..."

# Stop and remove containers, networks, and volumes created by 'docker-compose up'
docker compose down

echo "Docker Compose services have been shut down and cleaned up."