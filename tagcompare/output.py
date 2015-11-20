"""Handles output files from the tagcompare tool
    - Creates output directories before a run
    - Compares the test configs with the result/output configs
    - Utility methods for getting the right path to outputs
"""
import settings
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

def makedirs():
    """Makes output directories in the structure of:
        - campaign
            - tagsizes
                - browser_configs
    """
    #if not os.path.exists(OUTPUT_DIR):
    #    os.makedirs(OUTPUT_DIR)

    campaigns = settings.DEFAULT.campaigns
    for cid in campaigns:
        c_dir = os.path.join(OUTPUT_DIR, str(cid))
        sizes = settings.DEFAULT.tagsizes
        for s in sizes:
            s_dir = os.path.join(c_dir, s)
            configs = settings.DEFAULT.configs
            for c in configs:
                m_dir = os.path.join(s_dir, c)
                if os.path.exists(m_dir):
                    continue
                os.makedirs(m_dir)


def getpath(cid, size=None, config=None):
    """Gets the output path for a given cid, size and config
    """
    result = os.path.join(OUTPUT_DIR, cid)
    if not size:
        return result

    result = os.path.join(result, size)
    if not config:
        return result

    result = os.path.join(result, config)
    return result

if __name__ == '__main__':
    makedirs()
