from multiprocessing.pool import ThreadPool
import json
from urllib import urlencode
import time

import requests

import settings
import logger

TIMESTAMP = time.strftime("%Y%m%d-%H%M%S")
LOGGER = logger.Logger(__name__).get()


class PlaceLocalApi:
    API_PREFIX = "api/v2/"

    def __init__(self, domain=None):
        if not domain:
            domain = settings.DEFAULT.domain
        self._domain = domain

    def get(self, route, prefix=API_PREFIX):
        url = str.format("https://{}/{}/{}", self._domain,
                         prefix, route)
        r = requests.get(
            url, headers=settings.DEFAULT.get_placelocal_headers())
        assert r.status_code == 200, "GET {} failed with{}".format(
            route, r.text)
        assert 'data' in r.text, "Invalid PL response - no data!"
        text = "".join(r.text.split())  # remove all whitespaces
        return json.loads(text)['data']

    def get_creative_family(self, cid):
        """
        Gets the latest creative family (draft) for a given campaign
        """
        families = self._get_creative_families(cid)
        last_id = families[-1]['id']
        return self._get_creative_family(last_id)

    def get_tags_for_campaigns(self, cids, ispreview=1):
        """
        Gets a set of tags for multiple campaigns:

        :param cids: a list of campaign ids
        :param ispreview: change to 1 to get preview tags, 0 by default
        :return: a dictionary of tags with the cid as key
        """
        if not cids:
            raise ValueError("cids not defined!")
        LOGGER.debug(
            "Get tags for %s campaigns: %s...", len(cids), cids)

        tp = ThreadPool(processes=10)
        results = {}
        for cid in cids:
            results[cid] = tp.apply_async(func=self.__get_tags,
                                          args=(cid, ispreview))
        all_tags = {}
        for cid in results:
            tags = results[cid].get()
            if not tags:
                LOGGER.warn("No tags found for cid %s" % cid)
                continue
            all_tags[cid] = tags
        LOGGER.debug("get_tags_for_campaigns for cids=%s returned:\n%s",
                     cids, all_tags)
        return all_tags

    def get_cids_from_settings(self, settings_obj=settings.DEFAULT):
        cids = settings_obj.campaigns
        pids = settings_obj.publishers
        return self._get_cids(cids, pids)

    """ Private functions """

    def __get_active_campaigns(self, pid):
        route = "publication/{}/campaigns?status=active".format(pid)
        data = self.get(route)
        campaigns = data['campaigns']

        result = []
        for c in campaigns:
            cid = c['id']
            result.append(cid)
        LOGGER.debug("Found %s active campaigns for publisher %s.  IDs: %s",
                     len(campaigns), pid, result)
        return result

    def __get_tags(self, cid, ispreview=1):
        """
        Gets a set of tags for a campaign,
        the key is its size and the value is the tag HTML
        :param cid: the campaign id
        :param ispreview: preview tags don't generate tracking traffic
        :return: tags data for all the tags of a given cid
        """
        # TODO: Support different protocols
        # protocol = ['http_ad_tags', 'https_ad_tags']
        route = "api/v2/campaign/{}/tags?".format(cid)

        # Animation time is set to 1 to make it static after 1s
        qp = urlencode(
            {"ispreview": ispreview,
             "isae": 0,
             "animationtime": settings.TAG_ANIMATION_TIME,
             "usetagmacros": 0})
        route += qp
        data = self.get(route)
        if not data:
            LOGGER.warning("No tags found for cid %s, tags data: %s", cid,
                           data)
            return None

        tags_data = data['http_ad_tags']
        return tags_data

    def _get_pids_from_publisher(self, pid):
        if not pid:
            raise ValueError("Invalid publisher id!")
        route = "api/v2/publisher/{}/publications".format(pid)
        data = self.get(route)
        if not data:
            return None

        publications = data['publications']
        pids = []
        for p in publications:
            pids.append(p['id'])
        return pids

    def _get_all_pids(self, pids):
        """
        Expand potential super publishers to get publishers from them
        :param pids:
        :return:
        """
        all_pids = []
        for pid in pids:
            newpids = self._get_pids_from_publisher(pid)
            if not newpids:
                all_pids.append(pid)
            else:
                all_pids += newpids
        result = list(set(all_pids))  # unique list
        LOGGER.debug("_get_all_pids: %s", result)
        return result

    def _get_cids(self, cids=None, pids=None):
        """
        Gets a list of campaign ids from a combinination of cids and pids
        :param cids: campaign ids, directly gets appended to the list of cids
        :param pids: publisher or superpub ids, this is confusing - I know
        :return: a list of campaign ids
        """
        if cids:
            return cids

        if not pids:
            raise ValueError("pids must be specified if there are no cids!")

        cids = []
        all_pids = self._get_all_pids(pids)
        for pid in all_pids:
            new_cids = self.__get_active_campaigns(pid)
            if new_cids:
                cids += new_cids
        return cids

    def _get_creative_families(self, cid):
        return self.get("campaign/{}/families".format(cid))

    def _get_creative_family(self, cf_id):
        return self.get(route="creativefamily/{}".format(cf_id))
