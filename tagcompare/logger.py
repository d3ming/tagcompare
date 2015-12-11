import os
import logging

import settings


class Logger(object):
    def __init__(self, name, directory=None, writefile=False):
        if directory and not writefile:
            raise ValueError(
                "directory was specified when writefile is False!")

        self.__directory = directory
        if writefile:
            if not directory:
                self.__directory = settings.DEFAULT.logdir
            if not os.path.exists(self.__directory):
                raise IOError(
                    "directory doesn't exist at {}".format(self.__directory))

        self.__name = name.replace('.log', '')
        logger = logging.getLogger('tagcompare.%s' % name)

        # Set default log levels
        logging.getLogger("tagcompare").setLevel(logging.DEBUG)
        if not logger.handlers:
            if writefile:
                logger.addHandler(self.__file_handler())
            logger.addHandler(self.__stream_handler())
        self._logger = logger

    @property
    def name(self):
        return self.__name

    @property
    def filepath(self):
        if not self.__directory:
            raise ValueError(
                'Cannot get filepath when there is no directory set!')
        return os.path.join(self.__directory, '%s.log' % self.__name)

    def __file_handler(self):
        handler = logging.FileHandler(self.filepath, mode='a')
        formatter = logging.Formatter(
            '%(levelname)s:%(asctime)s %(name)s %(message)s')
        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)
        return handler

    def __stream_handler(self):
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        handler.setLevel(settings.LOG_LEVEL)
        return handler

    def get(self):
        return self._logger
