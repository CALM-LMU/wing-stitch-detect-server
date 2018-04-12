from xmlrpc.server import SimpleXMLRPCServer
import argparse

from calmutils.segmentation import Tools
from calmutils.imageio import read_bf


class Worker:
    def __init__(self, unet_conf_dir):
        self.tools = Tools(unet_conf_dir)

    def __call__(self, img_path):
        try:
            return self.tools.predict_bbox(read_bf(img_path))
        except Exception:
            return []


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('unet_dir', help='directory of U-net project')
    parser.add_argument('-p', '--port', help='port to listen on')

    args = parser.parse_args()

    server = SimpleXMLRPCServer(("localhost", int(args.port)))
    server.register_function(Worker(args.unet_dir), "detect_bbox")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()