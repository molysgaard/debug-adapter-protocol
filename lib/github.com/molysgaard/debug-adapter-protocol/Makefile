all: test  sml-debug-adapter

test: test.mlb out.sml
	mlton test.mlb

out.sml: jsonschema_test.py
	python jsonschema_test.py > out.sml

sml-debug-adapter: sml-debug-adapter.sml
	mlton sml-debug-adapter.sml
