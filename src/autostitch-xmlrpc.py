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
    parser.add_argument('-p', '--port', help='port to listen on')
    parser.add_argument('-i', '--interface', help='inteface to listen on')
    parser.add_argument('-n', '--num_workers', help='inteface to listen on')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        level=logging.DEBUG,
                        datefmt='%d.%m.%Y %H:%M:%S')
    logger = logging.getLogger(__name__)


    if not os.path.exists(args.fiji):
        parser.print_help()
        logger.error('fiji executable not found')
        sys.exit(1)

    processor = AsyncFileProcesser(args.fiji,
                                   os.path.join(os.path.abspath(__file__).rsplit(os.sep, 2)[0], 'res', 'stitch.ijm' ),
                                   os.path.join(os.path.abspath(__file__).rsplit(os.sep, 2)[0], 'res', 'stitch_tiff.ijm'),
                                   int(args.num_workers if args.num_workers else 8))

    server = SimpleXMLRPCServer((get_ip(args.interface if args.interface else 'eth0'), int(args.port if args.port else 8001)),allow_none=True)
    server.register_function(processor, "stitch")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        try:
            print('Interrupted, waiting for stitching to finish. Press Ctrl-C again to quit immediately.')
            processor.quit()
            print('All stitching tasks completed.')
        except KeyboardInterrupt:
            pass
        finally:
            print('Done.')

if __name__ == '__main__':
    main()
