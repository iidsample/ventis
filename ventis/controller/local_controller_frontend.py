# Local Controller Frontend - gRPC Server
# Accepts incoming Execute requests and pushes them into a Python queue for processing.

import grpc
from concurrent import futures
import subprocess
import os
import signal
from collections import defaultdict
from threading import Lock, Thread
import json
import time
import redis
import traceback
import queue
import logging
import sys
import os

# Add grpc_stubs to the path so generated protobuf modules are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "grpc_stubs"))

import local_controler_pb2
import local_controler_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LocalControllerServicer(local_controler_pb2_grpc.LocalControllerServicer):
    """gRPC servicer that accepts requests and pushes them into a queue."""

    def __init__(self):
        self.request_queue = queue.Queue()
        # Redis client for writing results back to local Redis
        redis_host = os.environ.get("VENTIS_REDIS_HOST", "localhost")
        redis_port = int(os.environ.get("VENTIS_REDIS_PORT", 6379))
        # Add utils to path for RedisClient
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "utils"))
        from redis_client import RedisClient
        self.redis = RedisClient(host=redis_host, port=redis_port)

    def Execute(self, request, context):
        """Accept an Execute request and push it into the queue."""
        logger.info(f"Received request: {request.resonse}")
        self.request_queue.put(request.resonse)
        return local_controler_pb2.JsonResponse(resonse="Request queued successfully")

    def WriteResult(self, request, context):
        """Accept a result or error from a remote controller and write it to local Redis."""
        try:
            data = json.loads(request.resonse)
            future_id = data.get("future_id")
            result = data.get("result")
            error = data.get("error")
            
            logger.info(f"WriteResult: received result for future {future_id}: {result}")
            if not result:
                logger.warning(f"WriteResult received empty/None result for future {future_id} from {context.peer()}")
                
            if future_id:
                if error is not None:
                    self.redis.hset(f"future:{future_id}", "error", error)
                    logger.info("WriteResult: wrote error for future %s", future_id)
                if result is not None:
                    self.redis.hset(f"future:{future_id}", "result", result)
                    logger.info("WriteResult: wrote result for future %s, result %s", future_id, result)
            else:
                logger.error("WriteResult: missing future_id in %s", data)
        except Exception as e:
            logger.error("WriteResult failed: %s", e)
        return local_controler_pb2.JsonResponse(resonse="Result written")


def start_server(port=50051):
    """Start the gRPC server."""
    servicer = LocalControllerServicer()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    local_controler_pb2_grpc.add_LocalControllerServicer_to_server(
        servicer, server
    )
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    logger.info(f"Local controller frontend started on port {port}")

    return server, servicer


if __name__ == "__main__":
    server, request_queue = start_server()
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        server.stop(0)

