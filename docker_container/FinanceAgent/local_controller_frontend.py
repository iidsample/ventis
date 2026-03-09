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

    def Execute(self, request, context):
        """Accept an Execute request and push it into the queue."""
        logger.info(f"Received request: {request.resonse}")
        self.request_queue.put(request.resonse)
        return local_controler_pb2.JsonResponse(resonse="Request queued successfully")


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

