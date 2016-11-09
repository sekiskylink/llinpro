install:
	pip install -r requirements/development.txt

clean:
	chmod +x ${PWD}/sh/clean.sh
	./scripts/clean.sh
