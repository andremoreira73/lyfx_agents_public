#!/bin/bash
if [ "$1" == "deploy" ]; then
    echo "Building and starting containers..."
    docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
    echo "Collecting static files..."
    docker compose -f docker-compose.prod.yml --env-file .env.prod exec web python manage.py collectstatic --noinput
    echo "Copying static files to host..."
    docker cp lyfx_agents_docker-web-1:/app/static/. ./static/
    echo "Deployment complete!"
else
    # All other commands pass through normally
    docker compose -f docker-compose.prod.yml --env-file .env.prod "$@"
fi