#################################################################################
# GLOBALS                                                                       #
#################################################################################

SHELL := /bin/sh

#################################################################################
# COMMANDS                                                                      #
#################################################################################


.PHONY: requirements
requirements:
	@uv sync

.PHONY: clean
clean:
	@find . -type f -name "*.py[co]" -delete
	@find . -type d -name "__pycache__" -exec rm -r {} +
	@find . -type d -name ".mypy_cache" -exec rm -r {} +
	@find . -type d -name ".pytest_cache" -exec rm -r {} +
	@find data -type d -name "album" -exec rm -r {} +
	@find data -type d -name "dump" -exec rm -r {} +
	@find data -type d -name "nested" -exec rm -r {} +
	@find . -type d -name ".trash" -exec rm -r {} +

.PHONY: data
data:
	@$(MAKE) --no-print-directory clean
	@uv run python -m scripts.duplicate data/source/ data/album
	@uv run python -m scripts.duplicate data/album
	@uv run python -m scripts.duplicate data/source/ data/dump
	@uv run python -m scripts.duplicate data/dump
	@uv run python -m scripts.duplicate data/source/ data/nested
	@uv run python -m scripts.duplicate data/source/ data/nested/dump

####################################################################################
################################ SMOKE TESTS: START ################################

SPACER="\n===============\n"
SECTION="\n\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\#\n\n"

.PHONY: test_intra_album
test_intra_album:
	@$(MAKE) --no-print-directory data
	@printf "%b%b" "\nINTRA-ALBUM: non-recursive" $(SECTION)
	ls data/album/ | head -n 5
	@printf $(SPACER)
	uv run photon dedupe --auto-select --force --silent data/album/ || true
	@printf $(SPACER)
	@printf "EXPECTED to fail: requires --intra flag"
	@printf $(SPACER)
	ls data/album/ | head -n 5
	@printf $(SPACER)
	@printf "EXPECTED: remove files of duplicated images with most counts of \"copy\" in the filename"
	@printf $(SPACER)
	uv run photon dedupe --auto-select --force --silent data/album/ --intra
	@printf $(SPACER)
	ls data/album/ | head -n 5

.PHONY: test_inter_album
test_inter_album:
	@$(MAKE) --no-print-directory data
	@printf "%b%b" "\nINTER-ALBUM: non-recursive" $(SECTION)
	ls data/album/ | head -n 5
	@printf $(SPACER)
	ls data/dump/ | head -n 5
	@printf $(SPACER)
	uv run photon dedupe -afs data/dump/ --ref data/album/
	@printf $(SPACER)
	@printf "EXPECTED: all files deleted in dump/"
	@printf $(SPACER)
	ls data/album/ | head -n 5
	@printf $(SPACER)
	ls data/dump/ | head -n 5
	@printf $(SPACER)

.PHONY: test_intra_album_recursive
test_intra_album_recursive:
	@$(MAKE) --no-print-directory data
	@printf "%b%b" "\nINTRA-ALBUM: recursive [no good selection criteria]" $(SECTION)
	ls data/nested/ | head -n 5
	@printf $(SPACER)
	ls data/nested/dump/ | head -n 5
	@printf $(SPACER)
	uv run photon dedupe -afs --recursive data/nested/ --intra
	@printf $(SPACER)
	@printf "EXPECTED: no files are deleted since there is no criteria to select files with same name"
	@printf $(SPACER)
	ls data/nested/ | head -n 5
	@printf $(SPACER)
	ls data/nested/dump/ | head -n 5
	@printf $(SPACER)

.PHONY: test_inter_album_recursive
test_inter_album_recursive:
	@$(MAKE) --no-print-directory data
	@printf "%b%b" "\nINTER-ALBUM: recursive" $(SECTION)
	ls data/nested/ | head -n 5
	@printf $(SPACER)
	ls data/nested/dump/ | head -n 5
	@printf $(SPACER)
	uv run photon dedupe -afs --recursive data/nested/ --ref data/album/
	@printf $(SPACER)
	@printf "EXPECTED: all files deleted in nested/ and dumb/"
	@printf $(SPACER)
	ls data/nested/ | head -n 5
	@printf $(SPACER)
	ls data/nested/dump/ | head -n 5
	@printf $(SPACER)

.PHONY: test_intra_album_interactive
test_intra_album_interactive:
	@$(MAKE) --no-print-directory data
	@printf "%b%b" "\nINTRA-ALBUM: recursive [interactive]" $(SECTION)
	ls data/nested/ | head -n 5
	@printf $(SPACER)
	ls data/nested/dump/ | head -n 5
	@printf $(SPACER)
	uv run photon dedupe --recursive data/nested/ --intra
	@printf $(SPACER)
	ls data/nested/ | head -n 5
	@printf $(SPACER)
	ls data/nested/dump/ | head -n 5
	@printf $(SPACER)

.PHONY: smoke
smoke:
	@clear
	@$(MAKE) --no-print-directory test_intra_album
	@echo
	@read -p "Press ENTER to continue…" _
	@clear
	@$(MAKE) --no-print-directory test_inter_album
	@echo
	@read -p "Press ENTER to continue…" _
	@clear
	@$(MAKE) --no-print-directory test_intra_album_recursive
	@echo
	@read -p "Press ENTER to continue…" _
	@clear
	@$(MAKE) --no-print-directory test_inter_album_recursive
	@echo
	@read -p "Press ENTER to continue…" _
	@clear
	@$(MAKE) --no-print-directory test_intra_album_interactive


################################ SMOKE TESTS: END   ################################
####################################################################################

.PHONY: lint
lint:
	@uv run mypy --strict src/
	@uv run pylint src/

.PHONY: format
format:
	@uv run black src/ tests/

.PHONY: test
test:
	@uv run pytest

## Soft diagnostics
.PHONY: precommit
precommit:
	@$(MAKE) --no-print-directory format || true
	@$(MAKE) --no-print-directory lint || true
	@$(MAKE) --no-print-directory test || true


.PHONY: git_precommit_hook
git_precommit_hook:
	@./scripts/git_enforce_staged.sh
	@uv run black --check src/ tests/
	@uv lock --check
	@$(MAKE) lint
	@$(MAKE) test
	@$(MAKE) clean
	@./scripts/git_enforce_staged.sh

#################################################################################
# Self Documenting Commands                                                     #
#################################################################################

.DEFAULT_GOAL := help

define PRINT_HELP_PYSCRIPT
import re, sys; \
lines = '\n'.join([line for line in sys.stdin]); \
matches = re.findall(r'\n## (.*)\n[\s\S]+?\n([a-zA-Z_-]+):', lines); \
print('Available rules:\n'); \
print('\n'.join(['{:25}{}'.format(*reversed(match)) for match in matches]))
endef
export PRINT_HELP_PYSCRIPT

.PHONY: help
help:
	@uv run python -c "${PRINT_HELP_PYSCRIPT}" < $(MAKEFILE_LIST)
