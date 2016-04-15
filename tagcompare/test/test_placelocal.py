import os
import json

import pytest

from tagcompare import settings
from tagcompare.placelocal import PlaceLocalApi


@pytest.fixture
def PlApi():
    # Test against QA and don't validate the response (so the test can)
    return PlaceLocalApi(domain='www.placelocalqa.com', validate=False)


def PlApiInvalid():
    return PlaceLocalApi(domain='www.placelocalqa.com', validate=True)


def test_invalid_requests():
    with pytest.raises(AssertionError):
        PlApiInvalid().get('bad/route')


def __read_json_file(jsonfile):
    with open(jsonfile) as f:
        return json.load(f)


def test_constructor_defaults():
    testApiClient = PlaceLocalApi()
    assert testApiClient


def __validate_tags(tags):
    expected_tags_file = os.path.join(settings.Test.TEST_ASSETS_DIR,
                                      "test_tags.json")
    actual_tags_file = 'tmp_tags.json'
    with open(actual_tags_file, 'w') as actual_tags:
        json.dump(tags, actual_tags)

    expected_tags = __read_json_file(expected_tags_file)
    actual_tags = __read_json_file(actual_tags_file)
    assert expected_tags == actual_tags, "tags don't match expected!"
    os.remove(actual_tags_file)


@pytest.mark.integration
def test_submit_campaign():
    response = PlApi().submit_campaign(cid=148548)
    assert response, "No response from test_submit_campaign"
    assert response.status_code == 200, "Invalid response from submit!"


@pytest.mark.integration
def test_get_tags_for_campaigns():
    cids = [148548, 148487]
    tags = PlApi().get_tags_for_campaigns(
        cids=cids, ispreview=0)
    assert tags, "Did not get tags for cid {}!".format(cids)

    __validate_tags(tags)
    for cid in tags:
        tags_per_campaign = tags[cid]
        assert len(tags_per_campaign) == 6, "Should have 6 sizes per campaign!"
        tags_per_size = tags_per_campaign['medium_rectangle']
        assert len(tags_per_size) == 2, "Should have 2 tags per size!"
        iframe_tag = tags_per_size['iframe']
        assert iframe_tag, "Should have iframe tag!"


@pytest.mark.integration
def test_get_tags_for_campaigns_invalid():
    cids = [999999]
    tags = PlApi().get_tags_for_campaigns(cids=cids)
    assert not tags, "Should not have gotten tags for an invalid cid!"

    with pytest.raises(ValueError):
        PlApi().get_tags_for_campaigns(cids=None)


@pytest.mark.integration
def test_get_cids_from_publications():
    pids = [647]
    cids = PlApi().get_all_cids(pids=pids, cids=None)
    assert cids, "Did not get any campaigns for pids: {}!".format(pids)
    assert len(cids) > 0, "Should have found some active campaigns!"
    print "Found {} campaigns for publishers: {}".format(len(cids), pids)


@pytest.mark.integration
def test_get_all_pids():
    pids = [486, 510]
    all_pids = PlApi()._get_all_pids(pids)
    assert len(all_pids) == 2
    assert 647 in all_pids


@pytest.mark.integration
def test_get_pids_from_publisher():
    with pytest.raises(ValueError):
        PlApi()._get_pids_from_publisher(pid=None)


def test_get_cids():
    cids = PlApi().get_all_cids(cids=[1, 2, 3])
    assert cids, "Could not get cids!"
    assert len(cids) == 3, "There should be exactly 3 cids!"


def test_get_cids_from_settings():
    settings_obj = settings.Settings(configfile='test/assets/test_settings.json',
                                     comparefile='test/assets/test_compare.json',
                                     logdir='test/assets/output/')
    cids = PlApi().get_cids_from_settings(settings_obj)
    assert 131313 in cids


def test_get_cids_invalid():
    with pytest.raises(ValueError):
        PlApi().get_all_cids()
