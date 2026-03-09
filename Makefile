stubs:
	mkdir -p stubs
	python src/stub_generator.py ./examples/finance_agent.yaml -o ./stubs/finance_agent_stub.py
	python src/stub_generator.py ./examples/market_agent.yaml -o ./stubs/market_agent_stub.py

grpc:
	mkdir -p grpc_stubs
	python -m grpc_tools.protoc -I./src/controller/proto --python_out=./grpc_stubs --grpc_python_out=./grpc_stubs ./src/controller/proto/global_controller.proto
	python -m grpc_tools.protoc -I./src/controller/proto --python_out=./grpc_stubs --grpc_python_out=./grpc_stubs ./src/controller/proto/local_controler.proto

docker:
	python src/stub_generator.py ./examples/finance_agent.yaml --agent-file ./examples/finance_agent.py --docker -o ./stubs/finance_agent_stub.py
	python src/stub_generator.py ./examples/market_agent.yaml --agent-file ./examples/market_agent.py --docker -o ./stubs/market_agent_stub.py
	docker build -t ventis-financeagent docker_container/FinanceAgent/
	docker build -t ventis-marketresearchagent docker_container/MarketResearchAgent/

all: stubs grpc docker

clean:
	rm -f ./stubs/*_stub.py
	rm -f ./grpc_stubs/*_pb2.py
	rm -f ./grpc_stubs/*_pb2_grpc.py
	rm -rf ./docker_container/

.PHONY: stubs grpc docker all clean
