import sys
import time
import logging
import multiprocessing
import subprocess
import shutil
import os
import argparse


def copy_lock(src, dst, copyfun=shutil.copy2, lock_ending='lock'):
    lock_file = '.'.join(dst if not os.path.isdir(dst) else os.path.join(dst, src.rsplit(os.sep, 1)[-1]), lock_ending)
    fd = open(lock_file, 'w')
    fd.close()

    copyfun(src, dst)
    os.rm(lock_file)


class AsyncFileProcesser:

    def __init__(self, fiji, script_nd2, script_tiff=None):
        self.procs = []
        self.fiji = fiji
        self.script_nd2 = script_nd2
        self.script_tiff = script_tiff if not script_tiff is None else script_nd2


    def __call__(self, args, tiff=False):
        # clean some old procs
        self.procs = [p for p in self.procs if p.is_alive()]

        if tiff:
            proc = multiprocessing.Process(target=self.fiji_call, args=(self.fiji, self.script_tiff, args))
        else:
            proc = multiprocessing.Process(target=self.fiji_call, args=(self.fiji, self.script_nd2, args))
        proc.start()

        self.procs.append(proc)


    def quit(self):
        for proc in self.procs:
            proc.join()


    @staticmethod
    def fiji_call(fiji, script, args):

        if not isinstance(args, list):
            args = [args, 50, 50, 1.0]
        if not os.path.exists(args[0] + '_stitched'):
            os.mkdir(args[0] + '_stitched')
        #TODO: move here?
        pr = subprocess.call([fiji, '--headless', '-macro', script, '"{} {} {} {}"'.format(args[0], int(args[1]), int(args[2]), float(args[3]))],
                stderr=subprocess.PIPE)
        print(pr.stderr)


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
