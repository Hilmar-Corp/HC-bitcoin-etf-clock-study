PYTHON ?= python

.PHONY: install lint test-public verify test-local assurance assurance-local freeze-evidence

install:
	$(PYTHON) -m pip install --require-hashes -r requirements/dev.lock.txt
	$(PYTHON) -m pip check

lint:
	test -s config/canonical_scripts.txt
	@while IFS= read -r f; do test -f "$$f" || { echo "Missing canonical file: $$f"; exit 1; }; done < config/canonical_scripts.txt
	$(PYTHON) -m ruff check $$(cat config/canonical_scripts.txt) tests tests_public scripts
	$(PYTHON) -m py_compile $$(cat config/canonical_scripts.txt)
	$(PYTHON) -m compileall -q tests tests_public scripts

test-public:
	$(PYTHON) -m pytest -q tests_public

verify:
	$(PYTHON) -m scripts.research.verify_repository

test-local:
	$(PYTHON) -m pytest -q tests

freeze-evidence:
	$(PYTHON) -m scripts.research.freeze_repository_evidence

assurance: lint test-public verify

assurance-local: assurance test-local
