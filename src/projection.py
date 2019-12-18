import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from skimage.external.tifffile import imread, imsave

from lib.StructuredAppearanceModelRegistration.process_image import projection


class ProjectorApplication(object):

    def __init__(self, n_parallel=1, *args, **kwargs):
        self.projector = projection.SharpnessBase2dProjection(*args, **kwargs)
        self.pool = ThreadPoolExecutor(max_workers=n_parallel)
        self.futures = []

    def change_projector_args(self, *args, **kwargs):
        # wait for all tasks to finish
        [f.result() for f in self.futures]
        self.futures = []
        self.projector = projection.SharpnessBase2dProjection(*args, **kwargs)

    def project(self, infiles, outfile_base, rgb=False, sharp_index=None, remove_infiles=False):
        self.futures.append(
            self.pool.submit(self._project, self.projector, infiles, outfile_base, rgb, sharp_index, remove_infiles))

    @staticmethod
    def _project(projector, infiles, outfile_base, rgb=False, sharp_index=None, remove_infiles=False):
        # TODO: check for erroneous input, ValueError

        os.makedirs(os.path.dirname(outfile_base), exist_ok=True)

        imgs = [imread(f) for f in infiles]
        # TODO: handle sharpness index
        projs, idxs = projector.project(imgs, ret_idx=True)

        idxs = idxs.astype(np.uint8)
        stack = np.stack(projs)
        if rgb:
            stack = stack.astype(np.uint8)

        imsave(outfile_base + '_projected.tif', stack, imagej=not rgb)
        imsave(outfile_base + '_idxes.tif', idxs)

        # removing input deactivated for now
        '''
        if remove_infiles:
            [os.remove(f) for f in infiles]
        '''