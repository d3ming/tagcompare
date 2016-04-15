import os

import pytest

from tagcompare import capture
from tagcompare.capture import TagCapture
from tagcompare import output


@pytest.fixture
def tagcapture_phantom():
    return TagCapture.from_config('phantomjs')


@pytest.mark.integration
def test_capture_configs():
    cids = [477944]
    configs = {
        "chrome": {
            "enabled": True,
            "capabilities": {
                "platform": "Windows 7",
                "browserName": "chrome"
            }
        },
        "chrome_beta": {
            "enabled": True,
            "capabilities": {
                "platform": "Windows 7",
                "browserName": "chrome",
                "version": "beta"
            }
        }}
    adsizes = ["medium_rectangle"]
    adtypes = ["iframe"]

    pb = output.create(build="capture_test")
    cm = capture.CaptureManager()
    errors = cm._capture_tags_for_configs(cids=cids, pathbuilder=pb,
                                          configs=configs,
                                          tagsizes=adsizes, tagtypes=adtypes,
                                          capture_existing=True)
    assert errors, "There should be at least one error!"
    pb.rmbuild()


@pytest.mark.integration
def test_capture_tag():
    tc = tagcapture_phantom()
    tag_htmls = {
        'div': '<div>Some text inside div</div>',
        'span': '<span>Some text inside span</span>'
    }

    for tagtype in tag_htmls:
        tag_html = tag_htmls[tagtype]
        output_path = tagtype + '_test.png'
        tc.capture_tag(tag_html, output_path, tagtype)
        assert os.path.exists(output_path), 'No output from capture_tag!'
        os.remove(output_path)


@pytest.mark.integration
def test_capture_tag_remote():
    """
    Verify that we can capture iframe and script tags
    :return:
    """
    pb = output.create(build="capture_tag_test", config="testconfig", cid="testcid",
                       tagsize="skyscraper", tagtype="iframe")
    tags = {"skyscraper": {
        "iframe": "<iframe>iframe tag for skyscraper</iframe>",
        "script": "<script>script tag for skyscraper</script>",
    }}

    capabilities = {
        "platform": "Windows 7",
        "browserName": "chrome"
    }

    remote_capture = TagCapture.from_caps(capabilities)
    __test_capture_tag(remote_capture, pb, tags)


def __test_capture_tag(tagcapture, pb, tags):
    result = tagcapture._capture_tag(pathbuilder=pb, tags_per_campaign=tags,
                                     capture_existing=True)
    tagcapture.close()
    assert result is not None, "Could not capture tags!"
    assert result is not False, "Tag capture skipped!"
    assert len(result) == 0, "Errors while capturing tags!"
    assert os.path.exists(pb.tagimage), "tagimage was not captured!"
    assert os.path.exists(pb.taghtml), "taghtml was not captured!"
    pb.rmbuild()
