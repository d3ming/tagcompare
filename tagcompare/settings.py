import json
import os
import logging

from enum import IntEnum


MODULE_NAME = "tagcompare"
DEFAULT_FILENAME = "settings.json"
DEFAULT_LOCAL_FILENAME = "settings.local.json"
DEFAULT_COMPARE_FILENAME = "compare.json"

OUTPUT_DIR = os.path.join("/tmp/", MODULE_NAME)
LOG_LEVEL = logging.INFO


class ImageErrorThreshold(IntEnum):
    NONE = 0,
    SLIGHT = 100,
    MODERATE = 250,
    BAD = 500,
    SEVERE = 1000


# Used by tests to access special conditions
TEST_MODE = False

"""
The animation time until the tag stops on the final frame
Setting animation time of 1 makes the ad transition to final frame after 1s
Any lower than this will cause incorrect animation transitions on the final frame
"""
TAG_ANIMATION_TIME = 1

""" Helper methods """


def get_unique_configs_from_comparisons(comparisons):
    tmpset = {}
    for comp in comparisons:
        complist = comparisons[comp]
        tmpset = set(tmpset).union(set(complist))

    unique_configs = list(tmpset)
    return unique_configs


def _get_enabled_items_in_dict(dictionary):
    return [item for item in dictionary if dictionary[item]]


def _get_abs_path(relpath):
    dirpath = os.path.abspath(os.path.dirname(__file__))
    abspath = os.path.join(dirpath, relpath)
    return abspath


def _load_json_file(relpath):
    return json.load(open(_get_abs_path(relpath), "r"))


class Settings():
    """The configuration class for tagcompare.
    reads settings.py and provides setting values to consumers
    """

    def __init__(self, configfile=DEFAULT_LOCAL_FILENAME,
                 comparefile=DEFAULT_COMPARE_FILENAME, logdir=OUTPUT_DIR):
        configfile_path = _get_abs_path(configfile)

        self.__logdir = _get_abs_path(logdir)
        if not os.path.exists(self.__logdir):
            os.makedirs(self.__logdir)

        if not os.path.exists(configfile_path):
            self.__configfile = _get_abs_path(DEFAULT_FILENAME)
            logging.warn(
                "Invalid configfile_path (%s), using default file at %s",
                configfile_path, self.__configfile)
        else:
            self.__configfile = configfile_path
        self.__settings = None
        self.__comparefile = comparefile
        self.__compare_set = None

    @property
    def logdir(self):
        return self.__logdir

    @property
    def _settings(self):
        if self.__settings:
            return self.__settings

        assert self.__configfile, "No config file specified!"
        assert os.path.exists(self.__configfile), \
            "Settings file not found at {}".format(self.__configfile)
        self.__settings = json.load(open(self.__configfile, "r"))
        return self.__settings

    @property
    def domain(self):
        return self.placelocal['domain']

    @property
    def tag(self):
        return self.__settings['tag']

    @property
    def tagsizes(self):
        return _get_enabled_items_in_dict(self.tag['sizes'])

    @property
    def tagtypes(self):
        return _get_enabled_items_in_dict(self.tag['types'])

    @property
    def campaigns(self):
        return self._settings['campaigns']

    @property
    def publishers(self):
        return self._settings['publishers']

    @property
    def webdriver(self):
        """
        Gets the remote webdriver settings to use

        saucelabs:
        https://wiki.saucelabs.com/display/DOCS/Platform+Configurator#/
        browserstack:
        https://www.browserstack.com/list-of-browsers-and-platforms?product=automate
        """
        webdriver_profiles = self._settings['webdriver']
        for name in webdriver_profiles:
            if webdriver_profiles[name]['enabled']:
                return webdriver_profiles[name]
        raise ValueError("No webdriver profile is marked as enabled!")

    @property
    def placelocal(self):
        return self._settings['placelocal']

    @property
    def _compare_set(self):
        """Loads compare.json and
        :return: the set of comparisons and configs from config.json
        """
        if self.__compare_set:
            return self.__compare_set

        self.__compare_set = _load_json_file(self.__comparefile)
        return self.__compare_set

    @property
    def comparisons(self):
        return self._compare_set['comparisons']

    @property
    def configs(self):
        return self._compare_set['configs']

    def configs_in_comparison(self):
        """Gets a list of unique configs from the comparisons matrix
        :return:
        """
        return get_unique_configs_from_comparisons(self.comparisons)


# TODO: not sure if this is proper...
DEFAULT = Settings()
