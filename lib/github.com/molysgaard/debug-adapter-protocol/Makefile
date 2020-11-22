all: dap  sml-debug-adapter

dap: dap.mlb dap.sml
	mlton dap.mlb

dap.sml: jsonschema_test.py
	python jsonschema_test.py > dap.sml

sml-debug-adapter: sml-debug-adapter.mlb sml-debug-adapter.sml
	mlton sml-debug-adapter.mlb

test-sml-debug-adapter: sml-debug-adapter
	printf "Content-Length: 384\r\n\r\n{\"command\":\"initialize\",\"arguments\":{\"clientID\":\"vscode\",\"clientName\":\"Visual Studio Code\",\"adapterID\":\"sml-debugger\",\"pathFormat\":\"path\",\"linesStartAt1\":true,\"columnsStartAt1\":true,\"supportsVariableType\":true,\"supportsVariablePaging\":true,\"supportsRunInTerminalRequest\":true,\"locale\":\"en-us\",\"supportsProgressReporting\":true,\"supportsInvalidatedEvent\":true},\"type\":\"request\",\"seq\":1}" | sml-debug-adapter
	cat /tmp/smlLog.txt
