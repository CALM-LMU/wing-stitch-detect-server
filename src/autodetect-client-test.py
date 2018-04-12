from xmlrpc.client import ServerProxy

with ServerProxy("http://localhost:8000/") as proxy:
    print(proxy.detect_bbox('acs'))

