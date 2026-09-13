# Tremor -- common tasks.  `make test` needs only numpy + scipy; everything else needs the
# TSB-AD data in data/ and the upstream clone in upstream/ (see README.md, "Reproduce").
PYTHON ?= python
WORKERS ?= 4

.PHONY: test install install-components clean tuning-u tuning-m eval-u

test:
	$(PYTHON) -m unittest discover -s tests -t . -v

install:
	$(PYTHON) -m pip install -e .

install-components:
	$(PYTHON) -m pip install -e ".[components]"

# the three U components on the Tuning set, then the chooser on the cached scores (0.6713 on 47 files)
tuning-u:
	$(PYTHON) harness/run.py --track U --split tuning --method MMPAD   --max-cost 6e10 --workers $(WORKERS)
	$(PYTHON) harness/run.py --track U --split tuning --method Sub_PCA --max-cost 6e10 --workers $(WORKERS)
	$(PYTHON) harness/run.py --track U --split tuning --method point --workers $(WORKERS)
	$(PYTHON) harness/fuse_eval.py --track U --split tuning \
	    --components U_tuning_MMPAD,U_tuning_Sub_PCA,U_tuning_point --tag _default

# the M components on the Tuning set, then the chooser (0.6373 on 15 files)
tuning-m:
	$(PYTHON) harness/run.py --track M --split tuning --method MMPAD --max-cost 1e11 --workers $(WORKERS)
	$(PYTHON) harness/run.py --track M --split tuning --method point_m --workers $(WORKERS)
	$(PYTHON) harness/run.py --track M --split tuning --method point_m_gate --workers $(WORKERS)
	$(PYTHON) harness/fuse_eval.py --track M --split tuning \
	    --components M_tuning_MMPAD,M_tuning_point_m,M_tuning_point_m_gate --tag _default

# end-to-end Tremor on the full U Eval list (~25 core-hours), compared with the published tables
eval-u:
	$(PYTHON) harness/run.py --track U --split eval --method Tremor --workers $(WORKERS)
	$(PYTHON) harness/eval_compare.py runs/U_eval_Tremor --save

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf build dist *.egg-info
