import random
import requests
from config import cfg
import grpc
import server_pb2
import server_pb2_grpc

def random_timeout():
    low = cfg.LOW_TIMEOUT
    high = cfg.HIGH_TIMEOUT
    return random.randrange(low, high) / 1000

def send(addr, route, message):
    try:
        timeout = cfg.REQUESTS_TIMEOUT / 1000
        reply = requests.post(
            url = addr + '/' + route,
            json=message,
            timeout=timeout,
        )
    except Exception as e:
        return None

    if reply.status_code == 200:
        return reply
    else:
        return None
    