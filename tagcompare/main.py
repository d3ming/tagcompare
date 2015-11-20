import os
import time

import image
import placelocal
import webdriver
import settings
import output


# TODO: Globals should get refactored into a settings file
# How long to wait for ad to load in seconds
WAIT_TIME_PER_AD = 7

# TODO: Remove
#TIMESTAMP = time.strftime("%Y%m%d-%H%M%S")
#OUTPUT_DIR = os.path.join("output", TIMESTAMP)

# https://www.browserstack.com/automate/capabilities
BROWSER_TEST_MATRIX = settings.DEFAULT.configs


def testcampaign(cid):
    tags = {}
    tags[cid] = placelocal.get_tags(cid=cid)
    if not tags or len(tags) == 0:
        print "No tags found, bailing..."
        return

    # Use remote browsers from browserstack
    configs = []
    for config in BROWSER_TEST_MATRIX:
        config_data = BROWSER_TEST_MATRIX[config]
        if not config_data['enabled']:
            continue

        configs.append(config)
        capabilities = config_data['capabilities']
        #output_dir = os.path.join(OUTPUT_DIR, config)
        webdriver.capture_tags_remotely(capabilities, tags, output.OUTPUT_DIR)

    image.compare_output(output.OUTPUT_DIR, configs=configs)


def main(cids=None, pid=None):
    # Input is a PID (pubilsher id) or a list of CIDs (campaign Ids)
    if not cids:
        if not pid:
            raise ValueError("pid must be specified if there are no cids!")
        cids = placelocal.get_active_campaigns(pid)

    output.makedirs()
    for cid in cids:
        testcampaign(cid)


if __name__ == '__main__':
    main(cids=settings.DEFAULT.campaigns, pid=settings.DEFAULT.publishers)
