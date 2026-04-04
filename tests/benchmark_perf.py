import sys
import os

from unittest.mock import MagicMock
import sys
sys.modules['firebase_admin'] = MagicMock()
sys.modules['firebase_admin.firestore'] = MagicMock()

import functions.mcp_network_server
functions.mcp_network_server.db = MagicMock()
from functions.mcp_network_server import MessageQueue
import time

mq = MessageQueue()
mq.messages_ref = MagicMock()

query_mock = MagicMock()
mq.messages_ref.document.return_value.collection.return_value.where.return_value.order_by.return_value.where.return_value.limit.return_value = query_mock
mq.messages_ref.document.return_value.collection.return_value.where.return_value.order_by.return_value.where.return_value.where.return_value.limit.return_value = query_mock

class MockDoc:
    def __init__(self, i):
        self.id = f"doc_{i}"
        self.data = {
            'type': 'test',
            'task_id': f'task_{i}',
            'acknowledged': False,
            'timestamp': '2023-01-01T00:00:00Z',
            'content': {'test': 'data' * 100},
            'description': 'test description',
            'reply_to': 'test reply to'
        }
    def to_dict(self):
        return self.data.copy()

def create_mock_stream(n):
    def stream():
        for i in range(n):
            yield MockDoc(i)
    query_mock.stream = stream

def run_benchmark(iterations):
    create_mock_stream(10)

    class NullWriter:
        def write(self, s):
            pass
        def flush(self):
            pass

    old_stdout = sys.stdout
    sys.stdout = NullWriter()
    start = time.time()
    for _ in range(iterations):
        messages = mq.get_messages("test_agent")
    end = time.time()
    sys.stdout = old_stdout

    return end - start

t = run_benchmark(1000)
print(f"Time taken (Optimized Code): {t:.4f} seconds")
