# chat_template

## API Documentation

Documentation is available at `/docs`

## Development

1. Run local service: `docker-compose up`
2. Check by url http://0.0.0.0:8061/api/ping


## Migration

1. docker compose run bot poetry run alembic init alembic - to create alembic files (execute only once during migration init)
2. docker compose run bot poetry run alembic revision --autogenerate (create migration, if db not up to date first upgrade than revision)
3. docker compose run bot poetry run alembic upgrade head (apply migration)


## Linters

1. pre-commit run black --all-files
2. pre-commit run isort --all-files
