.PHONY: install run debug clean lint lint-strict uv

py := python3

install:
	uv sync
run:
	uv run $(py) main.py $(input)

debug:
	$(py) -m pdb a_maze_ing.py config.txt

clean:
	rm -rf __pycache__ .mypy_cache

lint:
	-flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	-flake8 .
	mypy . --strict