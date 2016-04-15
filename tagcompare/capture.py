#!/usr/bin/env python

from multiprocessing.pool import ThreadPool
import os

import selenium

import placelocal
import webdriver
from webdriver import WebDriverType
import output
import settings
import logger


class TagCapture(object):
    """TagCapture uses webdriver to capture tags for campaigns"""

    def __init__(self, configname, driver, caps=None,
                 wait_for_load=True, wait_time=3, placelocal_api=None):
        self.logger = logger.Logger(name="capture", writefile=True).get()
        self._configname = configname
        self._driver = driver
        self._caps = caps
        self._wait_time = wait_time
        self._wait_for_load = wait_for_load
        if not placelocal_api:
            placelocal_api = placelocal.PlaceLocalApi()
        self.logger.debug('Initialized TagCapture with caps: %s', self._caps)

    def close(self):
        self.logger.debug("Closing webdriver...")
        try:
            self._driver.quit()
        except Exception as ex:
            self.logger.warn(
                "Exception closing webdriver: %s", ex, exc_info=True)

    @classmethod
    def from_config(cls, configname, buildname=None,
                    wait_time=3, wait_for_load=True):
        if configname == 'phantomjs':
            driver = webdriver.setup_webdriver(
                drivertype=WebDriverType.PHANTOM_JS)
            caps = configname
            # Override wait_for_load since it doesn't work with phantomjs
            # Override wait_time on tag render for phantomjs to be shorter
            wait_for_load = False
            wait_time = 1
        else:
            caps = TagCapture.__get_capabilities_for_config(
                configname, buildname)
            driver = webdriver.setup_webdriver(drivertype=WebDriverType.REMOTE,
                                               capabilities=caps)
        return cls(configname, driver, caps,
                   wait_time=wait_time, wait_for_load=wait_for_load)

    @classmethod
    def from_caps(cls, caps):
        browsername = caps['browserName']
        browserversion = caps.get('version') or ''
        configname = browsername + browserversion
        driver = webdriver.setup_webdriver(drivertype=WebDriverType.REMOTE,
                                           capabilities=caps)
        return cls(configname, driver, caps)

    def capture_tag(self, tag_html, output_path, tagtype='iframe'):
        """
        Generic/public method to capture a tag
        :param driver:
        :param tag_html:
        :param output_path:
        :param tagtype:
        :return:
        """
        errors = webdriver.display_tag(self._driver, tag_html,
                                       wait_time=self._wait_time)
        tag_element = self._driver.find_element_by_tag_name(tagtype)
        webdriver.screenshot_element(
            self._driver, tag_element, output_path)
        self.logger.debug('capture_tag complete for %s', output_path)
        return errors

    def _capture_tag(self, pathbuilder, tags_per_campaign, capture_existing):
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
            self.logger.debug("Skipping existing captures %s", default_pb.path)
            return None

        tag_html = tags_per_campaign[pathbuilder.tagsize][pathbuilder.tagtype]
        pathbuilder.create()
        output_path = pathbuilder.tagimage
        errors = self.capture_tag(tag_html=tag_html, output_path=output_path,
                                  tagtype=pathbuilder.tagtype)
        self.__write_html(
            tag_html=tag_html, output_path=pathbuilder.taghtml)
        return errors

    def capture_tags(self, tags, pathbuilder,
                     tagsizes=settings.DEFAULT.tagsizes,
                     tagtypes=settings.DEFAULT.tagtypes,
                     capture_existing=False):
        num_existing_skipped = 0
        num_captured = 0
        browser_errors = []
        self.logger.info('capture_tags for %s tags with driver: %s',
                         len(tags), self.driver)

        for cid in tags:
            pathbuilder.cid = cid
            tags_per_campaign = tags[cid]
            # LOGGER.debug("tags_per_campaign: %s", str(tags_per_campaign))
            # TODO: Refactor better with _capture_tag
            # It's weird that we pass in a pathbuilder object and do two
            # nested loops here
            for tagsize in tagsizes:
                if tagsize not in tags_per_campaign:
                    self.logger.warn("No tagsize '%s' found for campaign: %s. Skipping",
                                     tagsize, cid)
                    continue
                pathbuilder.tagsize = tagsize
                for tagtype in tagtypes:
                    pathbuilder.tagtype = tagtype
                    try:
                        r = self._capture_tag(pathbuilder=pathbuilder,
                                              tags_per_campaign=tags_per_campaign,
                                              capture_existing=capture_existing)
                    except selenium.common.exceptions.WebDriverException as e:
                        self.logger.error("Exception while capturing tags: %s",
                                          e, exc_info=True)
                        continue

                    # Increment results
                    if r is None:
                        self.logger.debug('Skipped: %s', pathbuilder.path)
                        num_existing_skipped += 1
                    elif r is False:
                        continue
                    else:
                        browser_errors += r
                        num_captured += 1
            self.logger.debug(
                "Captured tags for campaign %s on %s", cid, self._caps)
        self.logger.info(
            "Captured %s tags, skipped %s existing tags for config=%s.  Found %s errors",
            num_captured, num_existing_skipped, self._caps, len(browser_errors))
        return browser_errors

    @staticmethod
    def __get_capabilities_for_config(configname, buildname=None, max_duration=9999,
                                      all_configs=None):
        if not all_configs:
            all_configs = settings.DEFAULT.all_configs
        assert configname in all_configs, 'configname not in all_configs!'
        config_data = all_configs[configname]
        assert config_data['enabled'], 'config not enabled!'
        capabilities = config_data['capabilities']
        capabilities['name'] = configname
        capabilities['maxDuration'] = max_duration
        capabilities['build'] = buildname
        return capabilities

    def __write_html(self, tag_html, output_path):
        if not output_path.endswith('.html'):
            output_path += ".html"

        if os.path.exists(output_path):
            return

        self.logger.debug("Writing html tag to file at %s", output_path)
        with open(output_path, 'w') as f:
            f.write(tag_html)


class CaptureManager():
    MAX_REMOTE_JOBS = 6

    def __init__(self):
        self.max_remote_jobs = 6
        self.logger = logger.Logger(name="capture", writefile=True).get()

    def _capture_tags_for_configs(self, cids, pathbuilder,
                                  configs,
                                  placelocal_api=None,
                                  tagsizes=settings.DEFAULT.tagsizes,
                                  tagtypes=settings.DEFAULT.tagtypes,
                                  capture_existing=True,
                                  multithread=True):
        # TODO: make capture_existing configurable
        # TODO: Implement progress bar
        # TODO: Reduce complexity
        def __capture_configs():
            errors = []
            buildname = 'tagcompare_' + pathbuilder.build
            for configname in configs:
                pathbuilder.config = configname
                cpb = pathbuilder.clone()
                tagcaptures[configname] = TagCapture.from_config(
                    configname, buildname)
                tagcapture_args = (
                    all_tags, cpb, tagsizes, tagtypes, capture_existing)
                if multithread:
                    captures[configname] = pool.apply_async(
                        func=tagcaptures[configname].capture_tags,
                        args=tagcapture_args)
                else:
                    errors += tagcaptures[configname].capture_tags(
                        all_tags, cpb, tagsizes, tagtypes,
                        capture_existing)

            if multithread:
                for configname in captures:
                    errors += captures[configname].get()
            return errors

        if not placelocal_api:
            placelocal_api = placelocal.PlaceLocalApi()
        all_tags = placelocal_api.get_tags_for_campaigns(cids=cids)
        if not all_tags:
            print("No tags found to capture!")
            return

        self.logger.info("Capturing tags for %s campaigns over %s configs", len(cids),
                         len(configs))

        # multi-thread the compare part because it's slow
        pool = ThreadPool(processes=CaptureManager.MAX_REMOTE_JOBS)
        captures = {}
        tagcaptures = {}

        errors = []
        try:
            errors = __capture_configs()
        except Exception as ex:
            self.logger.errors("Exception during _capture_tags_for_configs: %s",
                               ex, exc_info=True)
        finally:
            if errors:
                self.logger.warn(
                    "%s found console errors:\n%s", pathbuilder.build, errors)
            return errors

            self.logger.info('Done with captures, closing browsers...')
            for configname in tagcaptures:
                tc = tagcaptures[configname]
                tc.close()

    def run(self):
        """
        Runs capture, returns the job name for the capture job
        :param cids:
        :param pids:
        :return: the original build string
        """
        placelocal_api = placelocal.PlaceLocalApi()

        original_build = output.generate_build_string()
        build = "capture_" + original_build
        pathbuilder = output.create(build=build)
        cids = placelocal_api.get_cids_from_settings()
        self.logger.info("Starting capture against %s for %s campaigns: %s...",
                         settings.DEFAULT.domain, len(cids), cids)
        output.aggregate()

        configs = settings.DEFAULT.configs_in_comparisons()
        self._capture_tags_for_configs(
            placelocal_api=placelocal_api,
            cids=cids, pathbuilder=pathbuilder, configs=configs)
        return original_build


def main():
    CaptureManager().run()

if __name__ == '__main__':
    main()
