import sys
import time
import logging
import subprocess
import shutil
import os
#import inspect
import argparse
from concurrent.futures import ThreadPoolExecutor
import re

from projection import ProjectorApplication

STITCHER_ENDING = '.tif'


def copy_lock(src, dst, copyfun=shutil.copy2, lock_ending='lock'):
    lock_file = '.'.join(dst if not os.path.isdir(dst) else os.path.join(dst, src.rsplit(os.sep, 1)[-1]), lock_ending)
    fd = open(lock_file, 'w')
    fd.close()

    copyfun(src, dst)
    os.rm(lock_file)


def split_str_digit(s):
    """
    split s into numeric (integer) and non-numeric parts
    return split as a tuple of ints and strings
    """
    res = []
    for m in re.finditer('(\d*)(\D*)', s):
        for g in m.groups():
            if g != '':
                try:
                    res.append(int(g))
                except ValueError:
                    res.append(g)
    return tuple(res)


def handle_cleanup(stitching_path, outpaths, outnames=None, raw_paths=None, delete_raw=True, delete_stitching=True):
    """
    cleanup after stitching is complete: move to output paths, delete temp files

    Parameters
    ----------
    stitching_path: str
        path containing stitching results (and no other STITCHER_ENDING files, e.g. raw data)
    outpaths: list of str
        n paths: path_i is path to copy channel_i to
    """

    # get natural-ordered stitched files (if we have more than 10 channels....)
    stitched_files = [f for f in os.listdir(stitching_path) if f.endswith(STITCHER_ENDING)]
    stitched_files.sort(key=lambda x: split_str_digit(x))

    # check same size -> raise ValueError if mismatch
    # this might be desired if we do not want to save stitched results at all

    if len(stitched_files) != len(outpaths) or (outnames and len(stitched_files) != len(outnames)):
        logging.error('number of files to copy and provided destinations mismatch')
        #raise ValueError('number of files to copy and provided destinations mismatch')

    # do the copy
    # we loop over output files, not input (to implicitly discard files we no longer want)
    for (idx, p) in enumerate(outpaths):
        shutil.copy2(os.path.join(stitching_path, stitched_files[idx]), os.path.join(p, outnames[idx] if outnames else stitched_files[idx]))

    # stitching is a directory -> remove
    if delete_stitching:
        shutil.rmtree(stitching_path)

    # raw paths can be files or dirs -> remove
    if delete_raw and raw_paths is not None:
        for raw_path in raw_paths:
            if os.path.isdir(raw_path):
                shutil.rmtree(raw_path)
            else:
                os.remove(raw_path)


class AsyncFileProcesser:

    def __init__(self, fiji, script_nd2, script_tiff=None, num_workers=1, debug=False):
        self.pool = ThreadPoolExecutor(max_workers=num_workers)
        self.fiji = fiji
        self.script_nd2 = script_nd2
        self.script_tiff = script_tiff if not script_tiff is None else script_nd2

        self.projector = ProjectorApplication()

        '''
        self.logger : logging.Logger = logging.getLogger('stitching.main')
        sh = logging.StreamHandler()
        sh.setLevel(logging.DEBUG if debug else logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        sh.setFormatter(formatter)
        self.logger.addHandler(sh)
        '''

    def __call__(self, args, tiff=False, cleanup_args=None, project=False):

        logging.debug('stitching pipeline called with arguments {}'.format(locals()))

        if tiff:
            self.pool.submit(self.fiji_call, *(self.fiji, self.script_tiff, args, cleanup_args, project))
        else:
            self.pool.submit(self.fiji_call, *(self.fiji, self.script_nd2, args, cleanup_args, project))


    def quit(self):

        logging.info('shutting down.')
        self.pool.shutdown()


    def fiji_call(self, fiji, script, args, cleanup_args=None, project=False):

        #logging.debug('called with arguments {}'.format(locals()))

        if not isinstance(args, list):
            args = [args, 50, 50, 1.0] if script is self.script_tiff else [args]

        #logging.debug('args for macro: {}'.format(args))
        if not os.path.exists(args[0] + '_stitched'):
            #logging.debug('mkingdir: {}'.format(args[0] + '_stitched'))
            os.mkdir(args[0] + '_stitched')
        #logging.debug('args for macro: {}'.format(args))

        logging.info('Stitching {} ...'.format(args[0]))

        with open(args[0] + '_stitch_log.txt', 'w') as fd:
            subprocess.run("{} --headless -macro {} '{}'".format(fiji, script, ' '.join(map(str, args))),
                                  stderr=subprocess.STDOUT, stdout=fd, shell=True, universal_newlines=True,
                                  encoding='utf-8')

        stitching_path = args[0] + '_stitched'
        logging.info('Stitching to {} DONE.'.format(stitching_path))
        logging.info('Stitching log written to {}'.format(args[0] + '_stitch_log.txt'))

        if project:


            logging.info('Projecting {} ...'.format(stitching_path))
            stitched_files = [f for f in os.listdir(stitching_path) if f.endswith(STITCHER_ENDING)]
            stitched_files.sort(key=lambda x: split_str_digit(x))

            outbase = args[0].replace('raw', 'projected')

            self.projector._project(self.projector.projector,
                                    infiles=[os.path.join(stitching_path, f) for f in stitched_files], outfile_base=outbase, rgb='RGB' in args)

            logging.info('Projection to {} DONE.'.format(outbase))
        if cleanup_args is not None:
            handle_cleanup(**cleanup_args)


class FolderWatcher:

    def __init__(self,
                 path,
                 callback,
                 endings=None,
                 lock_endings=None,
                 logger=None,
                 ignore_existing=True,
                 check_interval=0.5):
        self.path = path
        self.callback = callback
        self.lock_endings = ['lock'] if lock_endings is None else lock_endings
        self.endings = endings

        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

        self.ignore_existing = ignore_existing
        self.check_interval = check_interval

        self.existing = set()
        self.new_files = set()

    def _start(self):
        if self.ignore_existing:
            self._check_new()
            for f in self.new_files:
                self.logger.info('ignoring existing file: {}'.format(f))
                self.existing.add(f)
            self.new_files.clear()

    def _check_new(self):

        # get all files
        raw_files = [f for f in os.listdir(self.path) if not os.path.isdir(os.path.join(self.path, f))]
        good_files = []

        for f in raw_files:

            # ignore hidden files
            if f.startswith('.'):
                continue

            # ignore lock files
            if f.rsplit('.', 1)[-1] in self.lock_endings:
                continue

            # filter endings
            if self.endings is not None:
                if f.rsplit('.', 1)[-1] not in self.endings:
                    continue

            # check if the file is locked
            locked = False
            for le in self.lock_endings:
                if '.'.join([f, le]) in raw_files:
                    locked = True
                    break
            if locked:
                continue

            good_files.append(f)

        for f in good_files:
            if not f in self.existing:
                self.logger.info('found new file: {}'.format(f))
                self.new_files.add(f)

    def _process_changes(self):
        for f in self.new_files:
            self.logger.info('processing new file: {}'.format(f))
            self.callback(os.path.join(self.path, f))
            self.existing.add(f)
        self.new_files.clear()

    def loop(self):
        self._start()

        while (True):
            try:

                self._check_new()
                self._process_changes()

                time.sleep(self.check_interval)

            # quit gracefully
            # we have the option to quit immediately, this should be OK, but ask anyway
            except KeyboardInterrupt:
                try:
                    self.logger.info('Keyboard interrupt received, quitting.')
                    self.logger.info('Waiting for processing steps to finish. Press Ctrl-C again to quit immediately.')
                    self.callback.quit()
                except KeyboardInterrupt:
                    self.logger.info('Quitting immediately.')
                finally:
                    self.logger.info('Finished.')
                    break


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('watch_dir', help='directory to watch for new files')
    parser.add_argument('fiji', help='path of the Fiji/ImageJ executable')
    parser.add_argument('-x', '--existing', help='process existing files', action='store_true')
    parser.add_argument('--macro',
                        help='path of an .ijm macro to execute for every new file ' +
                             '(must take exactly one parameter: path of the file)')
    parser.add_argument('-e', '--endings',
                        help='restrict processing to files with given endings (comma-separated list)')
    parser.add_argument('-l', '--lock',
                        help='possible endings of lock files (comma-separated list)')
    parser.add_argument('-d', '--debug', help='show debug output', action='store_true')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        level=logging.DEBUG if args.debug else logging.INFO,
                        datefmt='%d.%m.%Y %H:%M:%S')
    logger = logging.getLogger(__name__)

    if not os.path.isdir(args.watch_dir):
        parser.print_help()
        logger.error('watch_dir is not a directory')
        sys.exit(1)

    if not os.path.exists(args.fiji):
        parser.print_help()
        logger.error('fiji executable not found')
        sys.exit(1)

    if args.macro and not os.path.exists(args.macro):
        parser.print_help()
        logger.error('macro file not found')
        sys.exit(1)

    processor = AsyncFileProcesser(args.fiji, args.macro if args.macro else os.path.join(os.path.abspath(__file__).rsplit(os.sep, 2)[0], 'res', 'stitch.ijm' ))
    watcher = FolderWatcher(args.watch_dir,
                            processor,
                            args.endings.split(',') if args.endings else None,
                            args.lock.split(',') if args.lock else None,
                            ignore_existing=not args.existing)
    watcher.loop()


if __name__ == '__main__':
    main()

"""
logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

proc = lambda f: 0
proc.quit = lambda: time.sleep(.2)
FolderWatcher('/data/agl_data/Analysis/notify-test/', proc).loop()
"""
