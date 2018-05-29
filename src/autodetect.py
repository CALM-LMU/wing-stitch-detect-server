from xmlrpc.server import SimpleXMLRPCServer
import argparse
import traceback

from calmutils.segmentation import Tools
from calmutils.imageio import read_bf
from calmutils.misc import filter_rprops

from skimage.transform import pyramid_gaussian
from skimage.io import imread

import netifaces as ni
import numpy as np


# filetypes to read with bioformates/imread (nd2 or tiff)
BF_ENDINGS = ['nd2']
IMREAD_ENDINGS = ['tif', 'tiff']


def get_ip(interface='eth0'):
    ni.ifaddresses(interface)
    ip = ni.ifaddresses(interface)[ni.AF_INET][0]['addr']
    return ip

class Worker:
    def __init__(self, unet_conf_dir):
        self.tools = Tools(unet_conf_dir)

    def __call__(self, img_path, existing_ds=4, filt=None):
        try:

            if img_path.split('.')[-1] in BF_ENDINGS:
                img = read_bf(img_path)
            elif img_path.split('.')[-1] in IMREAD_ENDINGS:
                img = imread(img_path)
            else:
                raise ValueError('Unknown file ending')

            print('read image of dtype {}'.format(img.dtype))
            if int(round(np.log2(4.0 / existing_ds))) >= 1:
                img = list(pyramid_gaussian(img, int(np.round(np.log2(4.0 / existing_ds)))))[-1]

            res = self.tools.predict(img)

            res2 = []
            for res_i in res:
                if filt is not None:
                    res2.append([ r.bbox for r in self.tools.get_regions(res_i) if filter_rprops(r, filt)])
                else:
                    res2.append([r.bbox for r in self.tools.get_regions(res_i)])
            return res2

        except Exception as e:
            traceback.print_exc()
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
