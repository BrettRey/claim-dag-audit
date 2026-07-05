.PHONY: setup test unit smoke example plan clean

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt && pip install -e . && pip install pytest

test: unit smoke

unit:
	. .venv/bin/activate && python -m pytest tests/ -q

smoke:
	. .venv/bin/activate && claim-dag validate examples/mini-paper/audits/claim-dag/2026-07-05
	. .venv/bin/activate && claim-dag argdown examples/mini-paper/audits/claim-dag/2026-07-05
	. .venv/bin/activate && claim-dag report examples/mini-paper/audits/claim-dag/2026-07-05

plan:
	. .venv/bin/activate && claim-dag plan examples/mini-paper/audits/claim-dag/2026-07-05

example: smoke

clean:
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	rm -rf build dist *.egg-info
