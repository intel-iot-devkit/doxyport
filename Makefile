# Author: Mircea Bardac <mircea.bardac@intel.com>

# default
.PHONE: default
default:
	@echo "Type \"make setup\" to download locally dependencies of DoxyPort"
	@echo "in a Python virtual environment."
	@echo

.PHONY: setup
setup:
	@which virtualenv >/dev/null || (echo "Setup requires \"virtualenv\" to be installed (pip install virtualenv)" && exit 1)
	rm -rf env
	virtualenv env
	bash -c "source env/bin/activate; pip install -r requirements.txt"
