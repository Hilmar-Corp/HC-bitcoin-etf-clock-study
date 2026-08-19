PYTHON ?= python

.PHONY: install lint test-public verify quant-verify test-local assurance assurance-local freeze-evidence quant-dd-local

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

quant-verify:
	$(PYTHON) -m scripts.research.verify_quant_dd

test-local:
	$(PYTHON) -m pytest -q tests

freeze-evidence:
	$(PYTHON) -m scripts.research.freeze_repository_evidence

assurance: lint test-public verify quant-verify

assurance-local: assurance test-local

quant-dd-local:
	$(PYTHON) -m scripts.research.coinbase_multivenue_sensitivity
	$(PYTHON) -m scripts.research.validate_etf_volume_blackrock
	$(PYTHON) -m scripts.research.analytical_core_coverage
	$(PYTHON) -m scripts.research.build_final_assurance
	$(PYTHON) -m scripts.research.freeze_repository_evidence
	$(MAKE) assurance
	$(MAKE) test-local
