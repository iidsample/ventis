import time
import json
import uuid
import sys
import os

# Add utils directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "utils"))

from redis_client import RedisClient

# defines the future object which will be returned by each function call
class Future(object):
    redis = RedisClient()

    def __init__(self, parent, service, method, args=None):
        """
        parent: parent future
        service: service to be called
        method: method to be called in service
        args: arguments to be passed to the method
        """
        
        # initial value of future object 
        self.id = uuid.uuid4().hex
        # this provides the funtionality we need to execute
        self.funtionality = None
        self.executor = None
        self.result = None
        self.parent = parent
        self.service = service
        self.method = method
        self.args = args or {}
        self.children = []
        self.consumers = []

        # Store scalar fields in a Redis Hash: future:<id>
        self.redis.hset_multiple(self._key(), {
            "id": self.id,
            "result": "",
            "parent": self.parent,
            "service": self.service,
            "method": self.method,
            "args": json.dumps(self.args),
        })

    def _key(self):
        """Redis key for this future's hash."""
        return f"future:{self.id}"

    def _children_key(self):
        """Redis key for this future's children set."""
        return f"future:{self.id}:children"

    def _consumers_key(self):
        """Redis key for this future's consumers set."""
        return f"future:{self.id}:consumers"

    def value(self, timeout=None):
        """
        This method will block until the value is computed or the timeout is reached.
        """
        if timeout is None:
            # block until the value is computed
            while self.result is None:
                time.sleep(0.001)
        else:
            start_time = time.time()
            while self.result is None and time.time() - start_time < timeout:
                # I havn't completely thought about the best way to handle this
                time.sleep(0.001)
            if self.result is None:
                raise TimeoutError(f"Future value not available within {timeout} seconds")
        return self.result

    # def __call__(self, timeout=None):
    #     """Allow calling the future directly to get the value, e.g. future()."""
    #     return self.value(timeout)

    def is_available(self):
        """
        This method will return True if the value is computed, False otherwise.
        """
        return self.result is not None

    def _get_children(self):
        """Return the list of children futures from Redis."""
        return self.redis.smembers(self._children_key())

    def _add_child(self, child):
        """Add a child future."""
        self.children.append(child)
        self.redis.sadd(self._children_key(), child)

    def _remove_child(self, child):
        """Remove a child future."""
        self.children.remove(child)
        self.redis.srem(self._children_key(), child)

    def _get_consumers(self):
        """Return the list of consumers from Redis."""
        return self.redis.smembers(self._consumers_key())

    def _add_consumer(self, consumer):
        """Add a consumer."""
        self.consumers.append(consumer)
        self.redis.sadd(self._consumers_key(), consumer)

    def _remove_consumer(self, consumer):
        """Remove a consumer."""
        self.consumers.remove(consumer)
        self.redis.srem(self._consumers_key(), consumer)
