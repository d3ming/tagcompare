from setuptools import setup
from setuptools.command.test import test as TestCommand
import sys


class Tox(TestCommand):
    user_options = [('tox-args=', 'a', "Arguments to pass to tox")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.tox_args = None

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import tox
        import shlex
        args = self.tox_args
        if args:
            args = shlex.split(self.tox_args)
        errno = tox.cmdline(args=args)
        sys.exit(errno)


setup(
    name='tagcompare',
    description='Capture and compare creative tags!',
    url='https://github.com/paperg/tagcompare',
    packages=['tagcompare', 'tagcompare.test'],
    install_requires=[
        'selenium',
        'requests',
        'pillow',
    ],
    package_data={
        '': ['*.json'],
    },
    tests_require=['tox'],
    cmdclass={'test': Tox},
)