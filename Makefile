.PHONY: install run test lint format docker-up docker-down clean

install:
	@echo 'Installing dependencies...'

run:
	@echo 'Running API...'

test:
	@echo 'Running tests...'

lint:
	@echo 'Linting codebase...'

format:
	@echo 'Formatting codebase...'

docker-up:
	@echo 'Starting Docker containers...'

docker-down:
	@echo 'Stopping Docker containers...'

clean:
	@echo 'Cleaning up...'
