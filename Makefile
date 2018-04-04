init:
	pip install pipenv!=11.3.2 --upgrade
	pipenv install --dev --skip-lock

test:
	py.test tests

lint:
	flake8

coverage:
	py.test tests --cov=musicview
	pip install codecov
	codecov
