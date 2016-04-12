#!/usr/bin/env python

import argparse
import sys
import logging

import capture
import compare
import settings
import logger
import setup


LOGGER = logger.Logger(name="main", writefile=True).get()


def __query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".

    Source: http://code.activestate.com/recipes/577058/
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


def __parse_params_to_settings():
    """
    Handles parsing commandline args and set appropriate settings from them
    :return: the key/value pair for the commandline args parsed
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture-only', action='store_true', default=False,
                        help='Run capture only without compare')
    parser.add_argument('-d', '--domain',
                        default=None,
                        help='Domain, i.e. www.placelocal.com')

    parser.add_argument('--verbose', action='store_true', default=False,
                        help='Enable verbose logging for debugging')
    parser.add_argument('--version', action='store_true', default=False,
                        help='Show version')

    # Either campaigns or publishers need to be specified, but not both
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('-c', '--campaigns', nargs='+',
                       help='Space separated list of campaign ids')
    group.add_argument('-p', '--publishers', nargs='+',
                       help='Space separated list of publisher ids')

    args = parser.parse_args()
    LOGGER.debug("tagcompare params: %s", args)
    return args


def __update_settings_from_args(args):
    # Update settings based on params
    if args.campaigns or args.publishers:
        settings.DEFAULT.campaigns = args.campaigns
        settings.DEFAULT.publishers = args.publishers

    if args.domain:
        settings.DEFAULT.domain = args.domain

    if args.verbose:
        settings.DEFAULT.loglevel = logging.DEBUG


def main():
    args = __parse_params_to_settings()

    if args.version:
        # This gets handled by setup.py, we just need to not run the main routine
        print(setup.git_version())
        exit(0)

    __update_settings_from_args(args)
    proceed = __query_yes_no("Start tagcompare against {} for cid={}, pids={}?"
                             .format(settings.DEFAULT.domain,
                                     settings.DEFAULT.campaigns,
                                     settings.DEFAULT.publishers))

    if not proceed:
        print("Stopping tagcompare on user input")
        exit(0)

    jobname = capture.main()
    if not args.capture_only:
        compare.main(build=jobname)


if __name__ == '__main__':
    main()
