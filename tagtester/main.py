#!/usr/bin/env python

import logging
import os
import argparse
import time
from contextlib import closing

from tagcompare import placelocal
from tagcompare import output
from tagcompare import settings
from tagcompare import capture
from tagcompare import image

import tests

MODULE_NAME = 'tagtester'
OUTPUT_BASEDIR = os.path.join(settings.HOME_DIR, MODULE_NAME)

DEFAULT_TEST_CONFIG = 'qa-core'


class TagTester(object):
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger('tagtester')
        self.args = self.__parse_args()
        self.__configure_logger(self.args.verbose)

        # Get config options
        self.test = self.get_test(self.args.test_config)
        self.logger.info('Test config: %s', self.test)
        self.placelocal = placelocal.PlaceLocalApi(domain=self.test['domain'])
        pids = self.test.get('pids')
        cids = self.test.get('cids')
        all_cids = self.placelocal.get_all_cids(
            pids=pids, cids=cids)
        self.cids = all_cids

    def get_test(self, testname):
        assert testname in tests.tests, "No test with name %s!" % (testname)
        return tests.tests[testname]

    def submit_campaigns(self, wait_time=60):
        bad_campaigns = []
        for cid in self.cids:
            self.logger.info('Re-submitting campaign %s', cid)
            try:
                self.placelocal.submit_campaign(cid)
            except AssertionError as err:
                self.logger.warn('Failed to submit campaign %s:\n%s!',
                                 cid, err, exc_info=True)
                bad_campaigns.append(cid)
                continue

        if bad_campaigns:
            self.logger.warn('%s campaigns failed submission:\n%s', len(bad_campaigns),
                             bad_campaigns)
        # It takes a minute or two after submit for it to take effect
        if wait_time > 0:
            self.logger.info('Waiting %s after submits...', wait_time)
            time.sleep(wait_time)

    def capture_tags(self, pb):
        self.logger.debug('Starting capture...')
        # TODO: Make reasonable defaults and refactor
        test_sizes = self.test['sizes']
        test_types = self.test['types']
        browser_configs = self.test.get('configs') or ['chrome']
        preview = self.test.get('preview') or 1

        #browser_errors = {}
        tag_count = 0
        for bc in browser_configs:
            tags = self.placelocal.get_tags_for_campaigns(
                cids=self.cids, ispreview=preview)
            pb.config = bc
            with closing(capture.TagCapture.from_config(bc)) as tagcapture:
                browser_errors = tagcapture.capture_tags(tags=tags, pathbuilder=pb, tagsizes=test_sizes,
                                                         tagtypes=test_types)

        if browser_errors:
            self.logger.error('Found browser errors in {} tags:\n{}'.format(
                len(browser_errors), browser_errors))
        else:
            self.logger.info(
                'Completed capture of {} tags'.format(tag_count))

    def compare_builds(self, build, reference='golden'):
        """
        Compares a build against a reference build, (by default named 'golden' build)
        :param buildname:
        :param golden:
        :return:
        """
        compare_build = build + "_vs_" + reference
        self.logger.info('Starting compare build: %s', compare_build)

        # Compare all the tag images in the build path against the golden set
        build_paths = output.get_all_paths(
            buildname=build, basedir=OUTPUT_BASEDIR)
        compare_errors = {}

        for bp in build_paths:
            build_pb = output.create_from_path(bp, basepath=OUTPUT_BASEDIR)

            # The reference build is included at the root level of tagtester
            ref_pb = build_pb.clone(
                build=reference, basepath=os.path.dirname(__file__))
            assert os.path.exists(
                ref_pb.buildpath), 'Reference build not found!'

            # We can compare iff both paths exists
            build_image = build_pb.tagimage
            ref_image = ref_pb.tagimage
            if not os.path.exists(build_image):
                self.logger.warn('SKIPPING compare: path does not exist at {}'.format(
                    build_pb.path))
                continue
            if not os.path.exists(ref_image):
                self.logger.warn('SKIPPING compare: path does not exist at {}'.format(
                    ref_pb.path))
                # TODO: In this case we want to have the option of making new
                # ref
                continue

            result = image.compare(build_pb.tagimage, ref_pb.tagimage)
            self.logger.debug('Result for %s: %s', compare_build, result)
            if result > settings.ImageErrorLevel.SLIGHT:
                compare_errors[build_image] = result
                self.logger.warn('Invalid compare result for %s', build_image)

        self.logger.info('Finished compare build %s for %s images!  Found %s errors:\n%s',
                         compare_build, len(build_paths), len(compare_errors), compare_errors)

    def __parse_args(self):
        """
        Handles parsing commandline args and set appropriate settings from them
        :return: the key/value pair for the commandline args parsed
        """
        parser = argparse.ArgumentParser()
        parser.add_argument('-b', '--compare-build',
                            default=None,
                            help='Specify a build name to compare with the reference set')
        parser.add_argument('-t', '--test-config',
                            default=DEFAULT_TEST_CONFIG,
                            help='Select a test config to run')

        parser.add_argument('-r', '--resubmit', action='store_true', default=False,
                            help='Used to resubmit every campaign before capture')
        parser.add_argument('-c', '--skip-capture', action='store_true', default=False,
                            help='Skips capture')

        parser.add_argument('--verbose', action='store_true', default=False,
                            help='Enable verbose logging for debugging')
        args = parser.parse_args()
        self.logger.debug("tagtester params: %s", args)
        return args

    def __configure_logger(self, verbose):
        if verbose:
            print('verbose logging mode!')
            level = logging.DEBUG
        else:
            level = logging.INFO

        ch = logging.StreamHandler()
        ch.setLevel(level)
        fh = logging.FileHandler('tagtester.log')
        fh.setLevel(logging.DEBUG)
        self.logger.addHandler(ch)
        self.logger.addHandler(fh)

    def run(self):
        self.logger.info(
            'Got %s campaigns from config: %s', len(self.cids), self.cids)

        if self.args.resubmit:
            self.submit_campaigns()

        if self.args.skip_capture:
            self.logger.info('Skipping capture due to config option!')
            return

        if not self.args.compare_build:
            build = output.generate_build_string(prefix=self.args.test_config)
            pb = output.create(build, basepath=OUTPUT_BASEDIR)
            self.capture_tags(pb=pb)
        else:
            build = self.args.compare_build

        self.compare_builds(build)

if __name__ == '__main__':
    tagtester = TagTester()
    tagtester.run()
