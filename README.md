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

## Workflow Context and Multi-Threading

Ventis uses Python's thread-local storage (`threading.local`) to transparently propagate request IDs from the `deploy.py` REST endpoint into the `Future` objects spawned by your workflow. This allows the Local Controller to look up policy context for your workflow's requests without cluttering your workflow code.

> [!WARNING]
> **Multi-threading inside a workflow:** Because the context is tied to the thread, if you manually spawn background threads *inside* your `workflow_fn`, those new threads will **not** inherit the request ID. If you need to spawn threads within a workflow, you must manually propagate the context:
> 
> ```python
> import ventis_context
> import threading
> 
> def my_workflow():
>     request_id = ventis_context.get_request_id()
>     
>     def background_task():
>         ventis_context.set_request_id(request_id)
>         # Your stubs/Futures created here will now correctly trace back to the request
>         
>     t = threading.Thread(target=background_task)
>     t.start()
> ```
> 
> **`asyncio` Incompatibility:** Because Ventis tracks requests via `threading.local()`, it is **not compatible** with Python's `asyncio` framework. Concurrent coroutines running on the same thread will blindly overwrite and leak each other's request IDs. Workflows must be written using standard synchronous Python or traditional threading.
