## makefile automates the build and deployment for python projects

# type of project
PROJ_TYPE=	python
PROJ_MODULES=	python-resources

# project
CONF_ARGS=	-c test-resources/garmdown.conf

include ./zenbuild/main.mk

.PHONY:		env
env:
		make PYTHON_BIN_ARGS='env $(CONF_ARGS)' run

.PHONY:		notdown
notdown:
		make PYTHON_BIN_ARGS='notdown -w 2 $(CONF_ARGS)' run

.PHONY:		sync
sync:
		make PYTHON_BIN_ARGS='sync $(CONF_ARGS)' run

.PHONY:		report
report:
		make PYTHON_BIN_ARGS='report $(CONF_ARGS) -f json' run

.PHONY:		sheet
sheet:
		make PYTHON_BIN_ARGS='sheet $(CONF_ARGS)' run

tmp:		info
		@echo $(PY_PKG_GUESS)
