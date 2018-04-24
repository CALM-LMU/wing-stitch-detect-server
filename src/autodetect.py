from xmlrpc.server import SimpleXMLRPCServer
import argparse

from calmutils.segmentation import Tools
from calmutils.imageio import read_bf
from calmutils.misc import filter_rprops

import netifaces as ni

def get_ip(interface='eth0'):
    ni.ifaddresses(interface)
    ip = ni.ifaddresses(interface)[ni.AF_INET][0]['addr']
    return ip

class Worker:
    def __init__(self, unet_conf_dir):
        self.tools = Tools(unet_conf_dir)

    def __call__(self, img_path, filt=None):
        try:
            res = self.tools.predict(read_bf(img_path))

            res2 = []
            for res_i in res:
                if filt is not None:
                    res2.append([ r.bbox for r in self.tools.get_regions(res_i) if filter_rprops(r, filt)])
                else:
                    res2.append([r.bbox for r in self.tools.get_regions(res_i)])
            return res2

        except Exception:
            return []


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('unet_dir', help='directory of U-net project')
    parser.add_argument('-p', '--port', help='port to listen on')
    parser.add_argument('-i', '--interface', help='inteface to listen on')

    args = parser.parse_args()

    server = SimpleXMLRPCServer((get_ip(args.interface if args.interface else 'eth0'), int(args.port if args.port else 8000)))
    server.register_function(Worker(args.unet_dir), "detect_bbox")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()