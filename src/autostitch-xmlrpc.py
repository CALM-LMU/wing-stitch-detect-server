from xmlrpc.server import SimpleXMLRPCServer
import argparse
import traceback
import netifaces as ni
import numpy as np
import os
import sys
import logging

from autostitch import AsyncFileProcesser
from autodetect import get_ip

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('fiji', help='path of the Fiji/ImageJ executable')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        level=logging.DEBUG,
                        datefmt='%d.%m.%Y %H:%M:%S')
    logger = logging.getLogger(__name__)


    if not os.path.exists(args.fiji):
        parser.print_help()
        logger.error('fiji executable not found')
        sys.exit(1)

    processor = AsyncFileProcesser(args.fiji, os.path.join(os.path.abspath(__file__).rsplit(os.sep, 2)[0], 'res', 'stitch.ijm' ))

    server = SimpleXMLRPCServer((get_ip('eth0'), 8001),allow_none=True)
    server.register_function(processor, "stitch")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
