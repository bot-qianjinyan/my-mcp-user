.PHONY: test test-api test-mcp test-e2e

test: test-api test-mcp

test-api:
	python -m pytest tests/api -q

test-mcp:
	python -m pytest tests/mcp -q

test-e2e:
	python -m pytest -m e2e -q
