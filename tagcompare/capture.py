from multiprocessing.pool import ThreadPool
import os

import selenium

import placelocal
import webdriver
import output
import settings
import logger


MAX_REMOTE_JOBS = 6
LOGGER = logger.Logger(name="capture", writefile=True).get()


def __capture_tags_for_configs(cids, pathbuilder,
                               configs,
                               tagsizes=settings.DEFAULT.tagsizes,
                               tagtypes=settings.DEFAULT.tagtypes,
                               capture_existing=False):
    all_tags = placelocal.get_tags_for_campaigns(cids=cids)
    if not all_tags:
        LOGGER.warn("No tags found to capture!")
        return

    LOGGER.info("Capturing tags for %s campaigns over %s configs", len(cids),
                len(configs))
    # TODO: Implement progress bar
    errors = []
    pool = ThreadPool(processes=MAX_REMOTE_JOBS)
    results = {}

    for config_name in configs:
        capabilities = webdriver.get_capabilities_for_config(
            config_name=config_name,
            build='tagcompare_' + pathbuilder.build,
            max_duration=3 * 60 * 60)

        pathbuilder.config = config_name
        cpb = pathbuilder.clone()
        results[config_name] = pool.apply_async(func=__capture_tags,
                                                args=(capabilities, all_tags, cpb,
                                                      tagsizes, tagtypes,
                                                      capture_existing))
    for config_name in results:
        errors += results[config_name].get()
    if errors:
        LOGGER.error("%s found console errors:\n%s", pathbuilder.build, errors)
    return errors


def __write_html(tag_html, output_path):
    if not output_path.endswith('.html'):
        output_path += ".html"

    if os.path.exists(output_path):
        return

    LOGGER.debug("Writing html tag to file at %s", output_path)
    with open(output_path, 'w') as f:
        f.write(tag_html)


def capture_tag(driver, tag_html, output_path, tagtype='iframe'):
    """
    Generic/public method to capture a tag
    :param driver:
    :param tag_html:
    :param output_path:
    :param tagtype:
    :return:
    """
    try:
        errors = webdriver.display_tag(driver, tag_html)
        tag_element = driver.find_element_by_tag_name(tagtype)
        webdriver.screenshot_element(driver, tag_element, output_path)
    except selenium.common.exceptions.WebDriverException:
        LOGGER.exception("Exception while capturing tags!")
        return False
    return errors


def __capture_tag(pathbuilder, tags_per_campaign, driver,
                  capture_existing=False):
    """
    Captures a tag
    :param pathbuilder:
    :param tags_per_campaign:
    :param tagsize:
    :param capabilities:
    :param capture_existing:
    :return: list of browser errors during capture.
        False on error, None on skip
    """
    # Check if we already have the files from default path
    default_pb = pathbuilder.clone(build=output.DEFAULT_BUILD_NAME)
    if default_pb.pathexists() and not capture_existing:
        LOGGER.debug("Skipping existing captures %s", default_pb.path)
        return None

    tag_html = tags_per_campaign[pathbuilder.tagsize][pathbuilder.tagtype]
    pathbuilder.create()
    output_path = pathbuilder.tagimage
    errors = capture_tag(driver=driver, tag_html=tag_html, output_path=output_path,
                         tagtype=pathbuilder.tagtype)
    __write_html(tag_html=tag_html, output_path=pathbuilder.taghtml)
    return errors


def __capture_tags(capabilities, tags, pathbuilder,
                   tagsizes=settings.DEFAULT.tagsizes,
                   tagtypes=settings.DEFAULT.tagtypes,
                   capture_existing=False):
    num_existing_skipped = 0
    num_captured = 0
    browser_errors = []
    driver = webdriver.setup_webdriver(capabilities)

    try:
        for cid in tags:
            pathbuilder.cid = cid
            tags_per_campaign = tags[cid]
            # LOGGER.debug("tags_per_campaign: %s", str(tags_per_campaign))
            # TODO: Refactor better with __capture_tag
            # It's weird that we pass in a pathbuilder object and do two nested loops here
            for tagsize in tagsizes:
                if tagsize not in tags_per_campaign:
                    LOGGER.warn("No tagsize '%s' found for campaign: %s. Skipping",
                                tagsize, cid)
                    continue
                pathbuilder.tagsize = tagsize
                for tagtype in tagtypes:
                    pathbuilder.tagtype = tagtype
                    r = __capture_tag(pathbuilder=pathbuilder,
                                      tags_per_campaign=tags_per_campaign,
                                      driver=driver,
                                      capture_existing=capture_existing)
                    if r is None:
                        num_existing_skipped += 1
                    elif r is False:
                        continue
                    else:
                        browser_errors += r
                        num_captured += 1
            LOGGER.debug("Captured tags for campaign %s on %s", cid, capabilities)
    except KeyboardInterrupt:
        driver.quit()
        driver = None
    finally:
        if driver:
            driver.quit()
    LOGGER.info(
        "Captured %s tags, skipped %s existing tags for config=%s.  Found %s errors",
        num_captured, num_existing_skipped, capabilities, len(browser_errors))
    return browser_errors


def main():
    """
    Runs capture, returns the job name for the capture job
    :param cids:
    :param pids:
    :return:
    """

    original_build = output.generate_build_string()
    build = "capture_" + original_build
    pathbuilder = output.create(build=build)
    cids = placelocal.get_cids_from_settings()
    LOGGER.info("Starting capture against %s for %s campaigns: %s...",
                settings.DEFAULT.domain,
                len(cids), cids)
    output.aggregate()

    configs = settings.DEFAULT.configs_in_comparisons()
    __capture_tags_for_configs(cids=cids, pathbuilder=pathbuilder, configs=configs)
    return original_build


if __name__ == '__main__':
    main()
