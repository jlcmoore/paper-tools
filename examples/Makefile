# Example paper Makefile. Use a full commit hash for PAPER_TOOLS_REV in each paper.
MAIN ?= main
ABSTRACT_TEX ?= $(MAIN).tex
ARXIV_CONFIG ?= arxiv_cleaner.yaml
ARXIV_ZIP ?= arxiv_submission.zip
ARXIV_ARGS ?=
PAPER_TOOLS_REV ?= v0.1.0
PAPER_TOOLS_SOURCE ?= \
	git+https://github.com/jlcmoore/paper-tools@$(PAPER_TOOLS_REV)
PAPER_TOOLS = uvx --from "$(PAPER_TOOLS_SOURCE)" paper-tools

.PHONY: all pdf abstract arxiv-clean

all: pdf

pdf:
	latexmk -pdf -interaction=nonstopmode -halt-on-error "$(MAIN).tex"

abstract:
	@$(PAPER_TOOLS) abstract "$(ABSTRACT_TEX)"

arxiv-clean:
	@$(PAPER_TOOLS) arxiv "$(MAIN).tex" \
		--config "$(ARXIV_CONFIG)" --output "$(ARXIV_ZIP)" $(ARXIV_ARGS)
