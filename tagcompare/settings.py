import json
import os


class Settings():
    """The configuration class for tagcompare.
    reads settings.py and provides setting values to consumers
    """

    def __init__(self, configfile="settings.local.json"):
        dirpath = os.path.abspath(os.path.dirname(__file__))
        configfile_path = os.path.join(dirpath, configfile)

        if not os.path.exists(configfile_path):
            # Use default config file if no override
            configfile_path = os.path.join(dirpath, "settings.json")

        self.__configfile = configfile_path
        self.__config = None

    @property
    def _settings(self):
        if self.__config:
            return self.__config

        assert self.__configfile, "No config file specified!"
        assert os.path.exists(self.__configfile), "Settings file not found at {}".format(self.__configfile)
        self.__config = json.load(open(self.__configfile, "r"))
        return self.__config

    @property
    def domain(self):
        return self.placelocal['domain']

    @property
    def tagsizes(self):
        return self._settings['tagsizes']

    @property
    def campaigns(self):
        return self._settings['campaigns']

    @property
    def publishers(self):
        return self._settings['publishers']

    @property
    def webdriver(self):
        return self._settings['webdriver']

    @property
    def placelocal(self):
        return self._settings['placelocal']

    @property
    def configs(self):
        return self.webdriver['configs']


DEFAULT = Settings()
