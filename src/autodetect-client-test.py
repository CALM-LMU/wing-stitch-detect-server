from xmlrpc.client import ServerProxy

with ServerProxy("http://localhost:8000/") as proxy:
    print(proxy.detect_bbox('/scratch/hoerl/NG_Overview_052.nd2', 1, {}))

