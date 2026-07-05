.PHONY: setup test example clean

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt && pip install -e .

test:
	. .venv/bin/activate && claim-dag validate examples/mini-paper/audits/claim-dag/2026-07-05
	. .venv/bin/activate && claim-dag argdown examples/mini-paper/audits/claim-dag/2026-07-05
	. .venv/bin/activate && claim-dag report examples/mini-paper/audits/claim-dag/2026-07-05

example: test

clean:
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	rm -rf build dist *.egg-info

