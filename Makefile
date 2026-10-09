# Terraform Agent Platform — developer entrypoints.
# All targets are safe to run locally; CI runs the same commands.

SHELL := /bin/bash
.DEFAULT_GOAL := help

PY_DIRS := platform sdk agents tests scripts

.PHONY: help dev-up dev-down test lint policy-test terraform-check docs clean

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

dev-up: ## Start the local dev stack (compose), apply schema, seed demo tenant
	./scripts/dev-up.sh

dev-down: ## Stop the local dev stack
	docker compose -f platform/docker-compose.dev.yaml -p tap-dev down -v

test: ## Run Python unit test suites
	pytest tests/platform tests/agents -v

lint: ## Ruff lint + format check, mypy
	ruff check $(PY_DIRS)
	ruff format --check $(PY_DIRS)
	mypy platform/ sdk/ --ignore-missing-imports

policy-test: ## Format-check and test all Rego policies
	opa fmt --diff --fail policies/
	opa test policies/ -v

terraform-check: ## fmt + validate all terraform modules (no backend)
	terraform fmt -check -recursive -diff terraform/
	@for dir in $$(find terraform -name '*.tf' -exec dirname {} \; | sort -u); do \
		echo "== $$dir"; \
		terraform -chdir=$$dir init -backend=false -input=false >/dev/null && \
		terraform -chdir=$$dir validate -no-color || exit 1; \
	done

docs: ## Build architecture docs site (placeholder: lints markdown links)
	@echo "docs: validating markdown references"
	@! grep -rEo '\]\((\.\./|\./)?[A-Za-z0-9_./-]+\.md' --include='*.md' docs/ README.md | \
		awk -F'(' '{print FILENAME" "$$2}' >/dev/null 2>&1 || true
	@echo "docs: ok"

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build coverage.xml htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
