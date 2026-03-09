# Ventis

Ventis is an agent orchestration framework that generates Future-returning Python stubs from YAML agent definitions, communicates over gRPC, and tracks execution state in Redis.

## Prerequisites

- **Python 3.10+**
- **Redis** — running on `localhost:6379` (default)
- **Python packages:**
  ```bash
  pip install pyyaml grpcio grpcio-tools redis
  ```

## Project Structure

```
ventis/
├── config/
│   └── global_controller.yaml  # Global controller agent config
├── examples/            # YAML agent definitions & example workflows
│   ├── finance_agent.yaml
│   ├── market_agent.yaml
│   └── workflow.py
├── src/
│   ├── stub_generator.py   # Generates Python stubs from YAML
│   ├── future.py            # Future object with Redis-backed state
│   └── controller/
│       ├── local_controller.py           # Local controller daemon
│       ├── local_controller_frontend.py  # gRPC servicer
│       ├── global_controller.py          # Global controller daemon
│       └── proto/                        # Protobuf definitions
├── stubs/               # Generated stub files (output)
├── grpc_stubs/          # Generated gRPC protobuf files (output)
├── utils/
│   └── redis_client.py  # Redis utility wrapper
└── Makefile
```

## Commands

All commands are run from the project root.

### Generate Agent Stubs

Reads the YAML agent definitions in `examples/` and generates Python stub files in `stubs/`:

```bash
make stubs
```

This runs:
```bash
python src/stub_generator.py ./examples/finance_agent.yaml -o ./stubs/finance_agent_stub.py
python src/stub_generator.py ./examples/market_agent.yaml  -o ./stubs/market_agent_stub.py
```

You can also generate a single stub manually:
```bash
python src/stub_generator.py <path/to/agent.yaml> -o <output_path.py>
```

### Generate gRPC Protobuf Stubs

Compiles the `.proto` definitions in `src/controller/proto/` into Python gRPC modules in `grpc_stubs/`:

```bash
make grpc
```

### Generate Everything

Run both stub generation and gRPC codegen in one step:

```bash
make all
```

### Start Redis

Redis must be running before executing any workflow, since `Future` objects store their state (id, result, parent, children, consumers) in Redis on creation.

```bash
redis-server
```

By default it listens on `localhost:6379`. To run it in the background:

```bash
redis-server --daemonize yes
```

### Run the Global Controller

The global controller is a daemon that maintains a routing table in Redis for all registered agents. It reads from `config/global_controller.yaml`:

```bash
python src/controller/global_controller.py
```

To use a custom config:
```bash
python src/controller/global_controller.py -c path/to/config.yaml
```

You can verify the routing table was written:
```bash
redis-cli HGETALL routing_table
```

### Run the Example Workflow

The example workflow demonstrates calling finance and market agent stubs. Make sure stubs and gRPC code are generated first, and that Redis is running:

```bash
python examples/workflow.py
```

### Clean Generated Files

Remove all generated stub and gRPC files:

```bash
make clean
```
