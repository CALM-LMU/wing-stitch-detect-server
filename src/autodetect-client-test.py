from xmlrpc.client import ServerProxy

with ServerProxy("gpu-1:8000/") as proxy:
    print(proxy.detect_bbox('/scratch/bunk/unet/images/test/000.tif'))

