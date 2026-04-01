# Local Controller
# Starts the gRPC frontend server and polls the request queue for incoming requests.
# Routes requests to the correct agent — either locally or by forwarding to another controller.

import json
import logging
import os
import sys
import time
import importlib.util

import grpc

from local_controller_frontend import start_server
from redis_client import RedisClient

# Add grpc_stubs directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "grpc_stubs"))

import local_controler_pb2
import local_controler_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROUTING_TABLE_KEY = "routing_table"
POLICY_RULES_KEY = "policy:rules"


class LocalController(object):
    """Manages the gRPC frontend and processes incoming requests from the queue."""

    def __init__(self, port=50051):
        self.port = port
        self.agent_host = os.environ.get("VENTIS_AGENT_HOST", "localhost")
        self.agent_name = os.environ.get("VENTIS_AGENT_NAME")
        self.agent_file = os.environ.get("VENTIS_AGENT_FILE")
        
        # Public port is how the routing table and other nodes know us;
        # internally the gRPC server binds to `port` (50051 inside Docker).
        self.public_port = os.environ.get("VENTIS_AGENT_PORT", str(port))
        
        self.server, self.servicer = start_server(port)
        self.request_queue = self.servicer.request_queue

        # Connect to Redis and report healthy status
        redis_host = os.environ.get("VENTIS_REDIS_HOST", "localhost")
        redis_port = int(os.environ.get("VENTIS_REDIS_PORT", 6379))
        self.redis = RedisClient(host=redis_host, port=redis_port)
        self._status_key = f"controller:{self.agent_host}:{self.public_port}:status"
        self.redis.set(self._status_key, "healthy")

        # My own endpoint for comparison with routing table
        self._my_endpoint = f"{self.agent_host}:{self.public_port}"

        # Cache for gRPC stubs to remote controllers
        self._remote_channels = {}  # endpoint -> grpc.Channel
        self._remote_stubs = {}     # endpoint -> LocalControllerStub

        # Policy rules cache (loaded lazily from Redis)
        self._policy_rules = None

        logger.info("Local controller initialized at %s, reported healthy to Redis.", self._my_endpoint)
        
        # Load the agent class dynamically
        self.agent = self._load_agent()

    def _load_agent(self):
        """Dynamically load and instantiate the agent class."""
        if not self.agent_name or not self.agent_file:
            logger.warning("VENTIS_AGENT_NAME or VENTIS_AGENT_FILE not set. Running without an agent.")
            return None

        agent_module_name = self.agent_file.replace(".py", "")
        
        # We assume the agent file is in the same directory as the local controller (e.g. copied by Docker)
        # or in the current working directory.
        agent_path = os.path.abspath(str(self.agent_file))
        
        if not os.path.exists(agent_path):
            logger.error(f"Agent file not found at {agent_path}")
            return None

        try:
            spec = importlib.util.spec_from_file_location(agent_module_name, agent_path)
            if spec is None or getattr(spec, "loader", None) is None:
                logger.error(f"Cannot find spec or loader for module {agent_module_name} at {agent_path}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[agent_module_name] = module
            spec.loader.exec_module(module)
            
            agent_class = getattr(module, self.agent_name)
            agent_instance = agent_class()
            logger.info(f"Successfully loaded and instantiated agent: {self.agent_name}")
            return agent_instance
        except Exception as e:
            logger.error(f"Failed to load agent {self.agent_name} from {agent_path}: {e}")
            return None

    # ------------------------------------------------------------------ #
    #  Policy evaluation                                                   #
    # ------------------------------------------------------------------ #

    def _load_policy_rules(self):
        """Load policy rules from Redis (cached after first load)."""
        if self._policy_rules is not None:
            return self._policy_rules

        rules_json = self.redis.get(POLICY_RULES_KEY)
        if rules_json:
            self._policy_rules = json.loads(rules_json)
        else:
            self._policy_rules = []
        return self._policy_rules

    def _check_policy(self, service, context):
        """
        Check if the given service is accessible for the given request context.

        Iterates through rules (sorted most-specific first) and returns True
        if a matching rule grants access to the service.
        """
        rules = self._load_policy_rules()
        if not rules:
            # No policy rules -> allow everything
            return True

        for rule in rules:
            match = rule.get("match", {})
            access = rule.get("access", [])

            # Check if all match keys are satisfied by the request context
            if all(context.get(k) == v for k, v in match.items()):
                if access == "all":
                    return True
                return service in access

        # No rule matched at all
        logger.warning("No policy rule matched for context=%s, denying access to %s", context, service)
        return False

    # ------------------------------------------------------------------ #
    #  Request processing                                                  #
    # ------------------------------------------------------------------ #

    def run(self):
        """Poll the request queue and process incoming requests."""
        logger.info("Local controller started, polling request queue...")
        try:
            while True:
                if not self.request_queue.empty():
                    raw = self.request_queue.get()
                    try:
                        data = json.loads(raw)
                        self._process_request(data)
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON in request: %s", raw)
                    except Exception as e:
                        logger.error("Error processing request: %s", e)
                else:
                    time.sleep(0.001)
        except KeyboardInterrupt:
            self.stop()

    def _process_request(self, data):
        """
        Route a request to the correct controller.

        Looks up the service in the routing table. If the endpoint matches
        this controller, execute locally. Otherwise, forward via gRPC.
        """
        service = data.get("service")
        function = data.get("function")
        args = data.get("args", {})
        future_id = data.get("future_id")
        origin = data.get("origin")  # endpoint of the LC that originated this request
        request_id = data.get("request_id")  # tracing ID from deploy module

        context = {}
        if request_id:
            context_json = self.redis.get(f"request:{request_id}:context")
            if context_json:
                context = json.loads(context_json)

        if not service or not function or not future_id:
            logger.error("Malformed request, missing required fields: %s", data)
            return

        # Check policy before routing
        if not self._check_policy(service, context):
            err_msg = f"Unauthorized: Policy denied access to service '{service}'"
            logger.warning(err_msg)
            self.redis.hset(f"future:{future_id}", "result", err_msg)
            if origin and origin != self._my_endpoint:
                self._send_result_callback(origin, future_id, err_msg)
            return

        # Look up the routing table
        endpoint = self.redis.hget(ROUTING_TABLE_KEY, service)
        if not endpoint:
            logger.error("No endpoint found for service '%s' in routing table.", service)
            return

        if endpoint == self._my_endpoint:
            self._execute_locally(service, function, args, future_id, origin)
        else:
            # Register the target as a consumer for any Future args
            # so results get pushed to its Redis via WriteResult.
            for key, value in args.items():
                if isinstance(value, str) and len(value) == 32 and all(c in "0123456789abcdefABCDEF" for c in value):
                    future_key = f"future:{value}"
                    if self.redis.hget(future_key, "id") is not None:
                        self.redis.sadd(f"{future_key}:consumers", endpoint)
                        logger.info("Registered %s as consumer of future %s (arg '%s')", endpoint, value, key)

                        # If the result is already available, push it immediately.
                        # This handles the race where _notify_consumers already ran.
                        existing_result = self.redis.hget(future_key, "result")
                        if existing_result is not None:
                            logger.info("Future %s already resolved, pushing result to %s", value, endpoint)
                            self._send_result_callback(endpoint, value, existing_result)

            logger.info("Forwarding %s.%s (future=%s) to %s", service, function, future_id, endpoint)
            self._forward_request(endpoint, data)

    def _resolve_future_args(self, args, poll_interval=0.01, timeout=300):
        """
        Check each arg value. If it is a 32-character hex string, assume it's
        a Future ID. Poll Redis until the result is available and replace
        the arg with the resolved value.
        """
        resolved = {}
        for key, value in args.items():
            # Check if this arg value is a UUID hex string identifying a future
            if isinstance(value, str) and len(value) == 32 and all(c in "0123456789abcdefABCDEF" for c in value):
                future_key = f"future:{value}"
                logger.info("Arg '%s' looks like a Future UUID (%s), waiting for result...", key, value)
                start = time.time()
                while True:
                    # print("Waiting for result for future next iteration %s", value)
                    result = self.redis.hget(future_key, "result")
                    if result is not None and result != "":
                        logger.info("Future %s resolved for arg '%s'", value, key)
                        resolved[key] = result
                        break
                    if time.time() - start > timeout:
                        raise TimeoutError(
                            f"Timed out waiting for future {value} (arg '{key}') "
                            f"after {timeout}s"
                        )
                    time.sleep(poll_interval)
                print("Resolved arg '%s' to %s", key, resolved[key])
            else:
                resolved[key] = value
        return resolved

    def _execute_locally(self, service, function, args, future_id, origin=None):
        """Execute a request on the local agent and write the result to Redis."""
        if self.agent is None:
            logger.error("No agent loaded, cannot execute %s.%s", service, function)
            return

        method = getattr(self.agent, function, None)
        if method is None:
            logger.error("Agent %s has no method '%s'", self.agent_name, function)
            return

        try:
            # Resolve any Future IDs in the args before executing
            args = self._resolve_future_args(args)

            logger.info("Executing %s.%s (future=%s) locally", service, function, future_id)
            result = method(**args)

            # Serialize the result
            if isinstance(result, (dict, list)):
                serialized = json.dumps(result)
            else:
                serialized = str(result)

            # Write result to local Redis
            self.redis.hset(f"future:{future_id}", "result", serialized)

            # If the request came from another node, send result back to origin
            if origin and origin != self._my_endpoint:
                self._send_result_callback(origin, future_id, serialized)

            logger.info("Completed %s.%s (future=%s) -> %s", service, function, future_id, serialized)
        except Exception as e:
            logger.error("Failed to execute %s.%s: %s", service, function, e)
            
            # Treat script-level crash as a string result to avoid hanging
            self.redis.hset(f"future:{future_id}", "result", f"Execution failed: {e}")
            if origin and origin != self._my_endpoint:
                self._send_result_callback(origin, future_id, f"Execution failed: {e}")

    # ------------------------------------------------------------------ #
    #  Request forwarding                                                  #
    # ------------------------------------------------------------------ #

    def _get_remote_stub(self, endpoint):
        """Get or create a cached gRPC stub for a remote controller."""
        if endpoint not in self._remote_stubs:
            self._remote_channels[endpoint] = grpc.insecure_channel(endpoint)
            self._remote_stubs[endpoint] = local_controler_pb2_grpc.LocalControllerStub(
                self._remote_channels[endpoint]
            )
            logger.info("Created gRPC connection to remote controller at %s", endpoint)
        return self._remote_stubs[endpoint]

    def _forward_request(self, endpoint, data):
        """Forward a request to a remote controller via gRPC."""
        # Tag the request with our endpoint so the remote LC can call back
        data["origin"] = self._my_endpoint
        stub = self._get_remote_stub(endpoint)
        request = local_controler_pb2.JsonResponse(resonse=json.dumps(data))
        try:
            stub.Execute(request)
            logger.debug("Forwarded request to %s", endpoint)
        except Exception as e:
            logger.error("Failed to forward request to %s: %s", endpoint, e)

    def _send_result_callback(self, origin, future_id, result):
        """Send a result back to the originating controller via WriteResult RPC."""
        stub = self._get_remote_stub(origin)
        payload = json.dumps({"future_id": future_id, "result": result})
        logger.info("Payload:Sent %s ", payload)
        request = local_controler_pb2.JsonResponse(resonse=payload)
        try:
            stub.WriteResult(request)
            logger.info("Sent result callback to %s for future %s, result %s", origin, future_id, result)

        except Exception as e:
            logger.error("Failed to send result callback to %s: %s", origin, e)

    # ------------------------------------------------------------------ #
    #  Shutdown                                                            #
    # ------------------------------------------------------------------ #

    def stop(self):
        """Gracefully shut down the server."""
        logger.info("Shutting down local controller...")
        self.redis.set(self._status_key, "stopped")
        self.server.stop(0)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=50051)
    args = parser.parse_args()

    controller = LocalController(port=args.port)
    controller.run()
