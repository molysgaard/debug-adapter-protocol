all: test.mlb out.sml
	mlton test.mlb

out.sml: jsonschema_test.py
	python jsonschema_test.py > out.sml

