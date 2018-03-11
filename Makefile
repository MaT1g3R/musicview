init:
	pip install pipenv!=11.3.2 --upgrade
	pipenv install --dev --skip-lock
	git submodule sync
	git submodule update --init

test:
	py.test tests

lint:
	flake8

coverage:
	py.test tests --cov=musicview
	pip install codecov
	codecov
