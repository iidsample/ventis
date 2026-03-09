# Local Controller
# Starts the gRPC frontend server and polls the request queue for incoming requests.

import logging
import time

from local_controller_frontend import start_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LocalController(object):
    """Manages the gRPC frontend and processes incoming requests from the queue."""

    def __init__(self, port=50051):
        self.server, self.servicer = start_server(port)
        self.request_queue = self.servicer.request_queue

        logger.info("Local controller initialized.")

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
        self.server.stop(0)


if __name__ == "__main__":
    controller = LocalController()
    controller.run()
