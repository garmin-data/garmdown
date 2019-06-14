## makefile automates the build and deployment for python projects

# type of project
PROJ_TYPE=	python
PROJ_MODULES=	python-resources

# project
CONFIG=		test-resources/garmdown.conf

include ./zenbuild/main.mk

.PHONY:		env
env:
		make PYTHON_BIN_ARGS='env -c $(CONFIG)' run

.PHONY:		notdown
notdown:
		make PYTHON_BIN_ARGS='notdown -w 2 -c $(CONFIG)' run

.PHONY:		sync
sync:
		make PYTHON_BIN_ARGS='sync -c $(CONFIG)' run

.PHONY:		report
report:
		make PYTHON_BIN_ARGS='report -c $(CONFIG) -f json' run

tmp:		info
		@echo $(PY_PKG_GUESS)
