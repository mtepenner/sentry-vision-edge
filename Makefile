.PHONY: build test up down lint

COMPOSE_FILE := orchestration/docker-compose.jetson.yml

# Build all Docker images
build:
	docker compose -f $(COMPOSE_FILE) build

# Run all tests
test: test-python test-go test-ts

test-python:
	cd vision_engine && pip install -q -r requirements.txt && python -m pytest tests/ -v

test-go:
	cd behavioral_brain && go test ./...

test-ts:
	cd command_dashboard && npm ci --prefer-offline && npx tsc --noEmit && npm test -- --watchAll=false

# Start the full stack
up:
	docker compose -f $(COMPOSE_FILE) up -d

# Stop the stack
down:
	docker compose -f $(COMPOSE_FILE) down

# Lint / type-check
lint: lint-go lint-ts

lint-go:
	cd behavioral_brain && go vet ./...

lint-ts:
	cd command_dashboard && npx tsc --noEmit
