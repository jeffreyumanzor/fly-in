export PYGAME_HIDE_SUPPORT_PROMPT=1
.PHONY: install run debug clean lint

install:
	uv sync

run:
	uv run main.py $(ARGS)

debug:
	uv run python -m pdb main.py $(ARGS)

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache output

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

test:
	uv run pytest