import pytest

from tagcompare import settings


@pytest.fixture
def config_obj():
    return settings.Settings('config.json')


def test_config():
    t = config_obj()._settings
    print "config:\n{}".format(t)
    assert t, "no settings object!"


def test_domain():
    t = config_obj().domain
    assert t, "domain undefined!"


def test_tagsizes():
    t = config_obj().tagsizes
    assert t, "tagsizes undefined!"
    assert len(t) > 0, "tagsizes has no values!"


def test_configs():
    t = config_obj().configs
    assert t, "configs undefined!"
    assert len(t) > 0, "configs has no values!"
