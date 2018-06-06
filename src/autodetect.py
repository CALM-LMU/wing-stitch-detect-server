from xmlrpc.server import SimpleXMLRPCServer
import argparse
import traceback

from calmutils.segmentation import Tools
from calmutils.imageio import read_bf
from calmutils.misc import filter_rprops

from skimage.transform import pyramid_gaussian
from skimage.io import imread, imsave
from skimage.measure import regionprops, label

import netifaces as ni
import numpy as np

from autostitch import AsyncFileProcesser


# filetypes to read with bioformates/imread (nd2 or tiff)
BF_ENDINGS = ['nd2']
IMREAD_ENDINGS = ['tif', 'tiff']


def get_ip(interface='eth0'):
    ni.ifaddresses(interface)
    ip = ni.ifaddresses(interface)[ni.AF_INET][0]['addr']
    return ip


def label_and_filter(img, filt=None):

    if filt is None:
        return label(img)

    # set objects rejected by filter to 0
    for r in regionprops(label(img)):
        (min_row, min_col, max_row, max_col) = r.bbox
        if not filter_rprops(r, filt):
            img[min_row:max_row, min_col:max_col][r.image] = 0

    return label(img)


class DetectionWorker:
    def __init__(self, unet_conf_dir):
        self.tools = Tools(unet_conf_dir)

    def __call__(self, img_path, existing_ds=4, filt=None, label_export_path=None):
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

            # export the labels
            # NB: we only export the first image of a stack
            #     as we only use single images at the moment, this should be fine
            if (label_export_path is not None) and len(res) > 0:
                lab = label_and_filter(res[0], filt).astype(np.uint16)
                imsave(label_export_path, lab)

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
    server.register_function(DetectionWorker(args.unet_dir), "detect_bbox")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
