import sys, requests

def redirect_to_leader(server_address, message):
    while True:
        method = requests.get if message["type"] == "get" else requests.put
        try:
            response = method(server_address + "/request", json=message, timeout=1)
        except Exception as e:
            return e
        if response.status_code == 200 and "payload" in response.json():
            payload = response.json()["payload"]
            if "message" in payload:
                server_address = payload["message"] + "/request"
            else:
                break
        else:
            break
    return response.json()

def put(addr, key, value):
    message = {"type": "put", "payload": {'key': key, 'value': value}}
    print(redirect_to_leader(addr, message))

def get(addr, key):
    message = {"type": "get", "payload": {'key': key}}
    print(redirect_to_leader(addr, message))

if __name__ == "__main__":
    if len(sys.argv) == 3:
        addr, key = sys.argv[1], sys.argv[2]
        get(addr, key)
    elif len(sys.argv) == 4:
        addr, key, val = sys.argv[1], sys.argv[2], sys.argv[3]
        put(addr, key, val)
    else:
        print("PUT usage: python3 client.py address 'key' 'value'")
        print("GET usage: python3 client.py address 'key'")
        print("Format: address: http://ip:port")