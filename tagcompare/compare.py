#!/usr/bin/env python

import os
import itertools
from multiprocessing.pool import ThreadPool

import settings
import placelocal
import logger
import output
import image


LOGGER = logger.Logger("compare", writefile=True).get()
NUM_COMPARE_PROCESSES = 8

placelocal_api = placelocal.PlaceLocalApi()


class CompareResult(object):
    def __init__(self):
        self.result = {
            settings.ImageErrorLevel.INVALID: 0,
            settings.ImageErrorLevel.NONE: 0,
            settings.ImageErrorLevel.SLIGHT: 0,
            settings.ImageErrorLevel.MODERATE: 0,
            settings.ImageErrorLevel.SEVERE: 0,
        }

        self.total = 0

    def __str__(self):
        return "CompareResult (total={}): \n {}".format(self.total, self.result)

    def increment(self, key):
        if key not in self.result:
            raise ValueError("Invalid key for results: %s", key)

        self.result[key] += 1
        self.total += 1
        return self.result


def __write_result_image(pathbuilder, result_image,
                         outputdir=None, info=None, prefix="merged"):
    if not outputdir:
        outputdir = pathbuilder.create(allow_partial=True)
    elif not os.path.exists(outputdir):
        os.makedirs(outputdir)

    filename = os.path.join(outputdir,
                            prefix + pathbuilder.tagname + ".png")
    LOGGER.debug("Saving merged image for %s to %s", pathbuilder.cid, filename)
    if info:
        result_image = image.add_info(result_image, info)
    result_image.save(open(filename, 'wb'))


def _get_compare_matrix(pathbuilder, configs):
    compare_pb = pathbuilder.clone(build=output.DEFAULT_BUILD_NAME)

    # Assumes all compared images will have the same dimensions, also that there is at
    # least one config.
    if len(configs) <= 0:
        LOGGER.error("Cannot build comparison matrix, no configs.")
        return None

    test_image = image.normalize_img(
        compare_pb.clone(config=configs[0]).tagimage)
    single_image_width = test_image.width
    single_image_height = test_image.height
    num_configs = len(configs)

    # Small optimization: we will reuse each image n times, so loading in advance
    # reduces number of loads to n from n^2.
    images_by_config = {}
    for cfg in configs:
        images_by_config[cfg] = image.normalize_img(
            compare_pb.clone(config=cfg).tagimage)

    # 2x2 comparison matrix, so it'll be kinda big.
    compare_image = image.blank_compare_matrix(num_configs, single_image_width,
                                               single_image_height)

    # 200 out of 255 for "approximately 80% opaque"
    difference_overlay_mask = image.get_overlay_mask(single_image_width,
                                                     single_image_height,
                                                     200)

    for a, b in itertools.combinations_with_replacement(range(len(configs)), 2):
        a_cfg = configs[a]
        b_cfg = configs[b]

        draw_position = (a * single_image_width, b * single_image_height)

        if a == b:
            # Special case, we know they'll be same image, so just render the
            # image.
            tagimage = image.normalize_img(
                compare_pb.clone(config=a_cfg).tagimage)
            image.add_label(image=tagimage, label=a_cfg)
            # Use 4-tuple for "draw_position"? Shouldn't be necessary since width and
            # height are invariant.
            image.draw_reference_copy(canvas=compare_image, srcimg=tagimage,
                                      position=draw_position)
        else:
            # Normal case, so we do a "comparison"
            a_img = images_by_config[a_cfg]
            b_img = images_by_config[b_cfg]
            cfgstring = a_cfg + " x " + b_cfg
            image.draw_visual_diff(canvas=compare_image, img1=a_img, img2=b_img,
                                   position=draw_position, cfgstring=cfgstring,
                                   overlay_mask=difference_overlay_mask)

    return compare_image


def _compare_configs(pathbuilder, configs, comparison, result):
    diff = _compare_configs_internal(pathbuilder=pathbuilder, configs=configs)
    if diff == settings.ImageErrorLevel.INVALID:
        result.increment(key=diff)
        return False

    result_image = _get_compare_matrix(
        pathbuilder=pathbuilder, configs=configs)

    prefix_label = comparison + "_"
    r = __handle_output(pathbuilder=pathbuilder, result_image=result_image,
                        diff=diff, prefix=prefix_label)
    result.increment(key=r)


def _compare_configs_internal(pathbuilder, configs):
    """
    Compares a given tag for all combinations of the specified list of configs
    :param pathbuilder: the pathbuilder pointing to the tag to compare
    :param configs: the list of configs to compare
    :return: the average diff from image comparison
    """
    total_diff = 0
    compare_pb = pathbuilder.clone(build=output.DEFAULT_BUILD_NAME)
    combo_count = 0
    for a, b in itertools.combinations(configs, 2):
        pba = compare_pb.clone(config=a)
        pbb = compare_pb.clone(config=b)
        pba_image = pba.tagimage
        pbb_image = pbb.tagimage
        if not os.path.exists(pba_image):
            LOGGER.error("File not found: %s", pba_image)
            return settings.ImageErrorLevel.INVALID
        if not os.path.exists(pbb_image):
            LOGGER.error("File not found: %s", pbb_image)
            return settings.ImageErrorLevel.INVALID
        total_diff += image.compare(pba.tagimage, pbb.tagimage)
        combo_count += 1
    return total_diff / combo_count


def compare(pb, cids, sizes=settings.DEFAULT.tagsizes,
            types=settings.DEFAULT.tagtypes,
            comparison="latest",  # TODO: Don't hardcode
            configs=None):
    if not configs:
        configs = settings.DEFAULT.all_comparisons[comparison]

    pool = ThreadPool(processes=NUM_COMPARE_PROCESSES)
    compare_threads = []
    result = CompareResult()
    LOGGER.info("Starting compare for %s campaigns over %s configs...",
                len(cids), len(configs))

    for cid in cids:
        for s in sizes:
            for t in types:
                newpb = pb.clone(cid=cid, tagsize=s, tagtype=t)
                compare_threads.append(pool.apply_async(func=_compare_configs,
                                                        args=(newpb, configs,
                                                              comparison, result)))
    for ct in compare_threads:
        ct.get()
    LOGGER.info("Compare over configs=%s, result=%s", configs, result)
    return result


def __handle_output(pathbuilder, result_image, diff, prefix=""):
    info = {"name": pathbuilder.tagname, "diff": diff}
    result = settings.ImageErrorLevel.NONE

    if diff > settings.ImageErrorLevel.SEVERE:
        prefix += "severe_"
        result = settings.ImageErrorLevel.SEVERE
    elif diff > settings.ImageErrorLevel.MODERATE:
        prefix += "moderate_"
        result = settings.ImageErrorLevel.MODERATE
    elif diff > settings.ImageErrorLevel.SLIGHT:
        prefix += "slight_"
        result = settings.ImageErrorLevel.SLIGHT
    __write_result_image(pathbuilder=pathbuilder, result_image=result_image,
                         info=info, prefix=prefix)
    return result


def main(build=None):
    LOGGER.info("Starting compare for cid=%s, pids=%s...",
                settings.DEFAULT.campaigns, settings.DEFAULT.publishers)
    output.aggregate()

    if not build:
        build = output.generate_build_string()
    jobname = "compare_" + build
    pb = output.create(build=jobname)

    cids = placelocal_api.get_cids_from_settings()
    compare(pb, cids=cids)
    return pb


if __name__ == '__main__':
    main()
