stubs:
	mkdir -p stubs
	python ventis/stub_generator.py ./examples/vllm_agent.yaml -o ./stubs/vllm_agent_stub.py
	python ventis/stub_generator.py ./examples/finance_agent.yaml -o ./stubs/finance_agent_stub.py
	python ventis/stub_generator.py ./examples/market_agent.yaml -o ./stubs/market_agent_stub.py

grpc:
	mkdir -p grpc_stubs
	python -m grpc_tools.protoc -I./ventis/controller/proto --python_out=./grpc_stubs --grpc_python_out=./grpc_stubs ./ventis/controller/proto/global_controller.proto
	python -m grpc_tools.protoc -I./ventis/controller/proto --python_out=./grpc_stubs --grpc_python_out=./grpc_stubs ./ventis/controller/proto/local_controler.proto

docker: stubs
	python ventis/stub_generator.py ./examples/vllm_agent.yaml --agent-file ./examples/vllm_agent.py --docker -o ./stubs/vllm_agent_stub.py
	python ventis/stub_generator.py ./examples/finance_agent.yaml --agent-file ./examples/finance_agent.py --docker --stub-files ./stubs/vllm_agent_stub.py -o ./stubs/finance_agent_stub.py
	python ventis/stub_generator.py ./examples/market_agent.yaml --agent-file ./examples/market_agent.py --docker -o ./stubs/market_agent_stub.py
	docker build -t ventis-vllmagent docker_container/VllmAgent/
	docker build -t ventis-financeagent docker_container/FinanceAgent/
	docker build -t ventis-marketresearchagent docker_container/MarketResearchAgent/

workflow-docker: stubs
	python ventis/stub_generator.py --workflow --workflow-file ./examples/workflow.py --stub-files ./stubs/finance_agent_stub.py ./stubs/market_agent_stub.py
	docker build -t ventis-workflow docker_container/Workflow/

all: stubs grpc docker workflow-docker

clean:
	rm -f ./stubs/*_stub.py
	rm -f ./grpc_stubs/*_pb2.py
	rm -f ./grpc_stubs/*_pb2_grpc.py
	rm -rf ./docker_container/

.PHONY: stubs grpc docker workflow-docker all clean
