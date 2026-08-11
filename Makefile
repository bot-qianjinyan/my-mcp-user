.PHONY: test test-api test-mcp

test: test-api test-mcp

test-api:
	python -m pytest tests/api -q

test-mcp:
	python -m pytest tests/mcp -q
