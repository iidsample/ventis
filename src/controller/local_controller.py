# Local Controller
# Starts the gRPC frontend server and polls the request queue for incoming requests.

import logging
import os
import time

from local_controller_frontend import start_server
from redis_client import RedisClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LocalController(object):
    """Manages the gRPC frontend and processes incoming requests from the queue."""

    def __init__(self, port=50051):
        self.port = port
        self.host = os.environ.get("VENTIS_REDIS_HOST", "localhost")
        self.server, self.servicer = start_server(port)
        self.request_queue = self.servicer.request_queue

        # Connect to Redis and report healthy status
        redis_host = self.host
        redis_port = int(os.environ.get("VENTIS_REDIS_PORT", 6379))
        self.redis = RedisClient(host=redis_host, port=redis_port)
        self._status_key = f"controller:{self.host}:{self.port}:status"
        self.redis.set(self._status_key, "healthy")

        logger.info("Local controller initialized, reported healthy to Redis.")

    def run(self):
        """Poll the request queue and process incoming requests."""
        logger.info("Local controller started, polling request queue...")
        try:
            while True:
                if not self.request_queue.empty():
                    request = self.request_queue.get()
                    logger.info(f"Processing request: {request}")
                    # TODO: Add request processing logic here
                else:
                    time.sleep(0.001)
        except KeyboardInterrupt:
            self.stop()

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
