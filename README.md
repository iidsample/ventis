# Ventis

Ventis is a lightweight agent orchestration framework designed for distributed workflows using gRPC and Redis.

## Core Features
- **Easy development and deployment**: Developers write agents in python as if writing single node local code. Ventis takes care of deployment and management of agents and workflows. Deployment engineers running this workflow can specify orchestration, authorization and other serving policies, Ventis will enforce them.     
- **Distributed Futures**: Asynchronous execution without any user workflow modification.
- **Pluggable Policy Engine**: Supports multiple policies for orchestration, authorization and other serving policies.

---

## Getting Started

### 1. Installation

```bash
git clone https://github.com/your-repo/ventis.git
cd ventis
pip install -e .
```

### 2. Prerequisites

- **Python 3.10+**
- **Docker** — Used to manage agents.

---

## Development Guide 

#### Step 1: Create a Project
```bash
ventis new-project my-app
cd my-app
```

#### Step 2: Define Your Agents
Place your agent logic (`.py`) and definitions (`.yaml`) in the `agents/` directory.

- **`agents/my_agent.yaml`**: Defines methods and schemas.
- **`agents/my_agent.py`**: Contains the actual Python implementation.

We have provided an example of a finance agent and a market research agent in the `examples/` directory. To run the example, copy files into your newly created project directory from within the your my-app directory with the command - 

```bash
cp -r ../examples/* ./
```

## Deployment Guide

#### Step 1: Configure the Global Controller
Edit `examples/config/global_controller.yaml` to list the agents you want to deploy, their hosts, ports, and resource limits.

#### Step 2: Build the project
```bash
ventis build
```
#### Step 2.1 (Only if performing distributed deployment):
If you are deploying agents and tools to multiple hosts, you need to make sure that the hosts are reachable from the machine where you are running the deploy command. To enable this please ensure that you have passwordless ssh access to the hosts. A guide to enable passwordless ssh access can be found [here](https://www.redhat.com/en/blog/passwordless-ssh).


#### Step 3: Deploy the project
```bash
ventis deploy
```

#### Step 4: Sending requests to the workflow

Upon running the deploy command, ventis automatically generates a REST API endpoint for the workflow. 
Users can send requests to this endpoint to trigger the workflow. For this example, workflow to send a request - 

```bash
curl -X POST http://localhost:8080/finance_workflow/run \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the current stock price of Apple?"
  }'
```

### Clean Generated Files

Remove all generated stub and gRPC files:

```bash
make clean
```

### Harnessing the power of Ventis
* Beyond an easy programming model and end-to-end deployment. Ventis, enables developers to write custom policies to perform fine-grained control over their agents, workflows. 
Currently, we support two types of policies, with plans to add more in the future. 

* **Authorization Policies**: Define rules based on the fields in the request to restrict agent access. For example, `examples/config/policy.yaml` defines rules to restrict access to the `FinanceAgent` to only authorized callers like 'CEO' or 'Analyst'. A developer can specify rules based on the fields in the request to restrict agent access.


* **Load Balancing & Efficiency**: Ventis has built-in policies to perform load-balancing across multiple instances of the same agent. Request migrations ease head-of-line blocking, and our experiments show that Ventis's performance control can reduce tail latencies and enable efficient GPU utilization. Here is an example of the results:

![Financial Analyst Results](images/financial_analyst_results_page.jpg)

For more details, please refer to our paper - [Nalar: An agent serving framework](https://arxiv.org/abs/2601.05109)




## Future Work

- **Dynamic Policy Updates**: Currently, policies are loaded as static yaml files at startup. We are actively working on adding mechanisms to dynamically update policies based on custom user code. Allowing developer for more flexible and dynamic policy management.

- **Agent Thread Safety**: The Local Controller now executes agent methods in a `ThreadPoolExecutor`. This means multiple requests can run concurrently on the same agent instance. Currently, agents are assumed to be stateless or thread-safe. If an agent has mutable shared state, concurrent calls could cause data corruption. Future improvements could include per-thread agent instances, a locking mechanism, or a configurable concurrency mode (e.g., serial vs. parallel execution per agent).
- **Stale Future Detection**: If an agent process crashes mid-execution, a Future's result may never be written to Redis, causing consumers to poll indefinitely. A TTL-based expiration or heartbeat mechanism could detect and clean up stale futures.
- **`asyncio` Support**: Ventis currently relies on `threading.local()` for request context propagation, which is incompatible with `asyncio`. Supporting `contextvars` would enable async workflow functions.


### Citation
If you find Ventis (Nalar) useful for your research, please cite our paper:
```bibtex
@misc{laju2026nalar,
      title={Nalar: An agent serving framework}, 
      author={Marco Laju and Donghyun Son and Saurabh Agarwal and Nitin Kedia and Myungjin Lee and Jayanth Srinivasa and Aditya Akella},
      year={2026},
      eprint={2601.05109},
      archivePrefix={arXiv},
      primaryClass={cs.DC},
      url={https://arxiv.org/abs/2601.05109}, 
}
```