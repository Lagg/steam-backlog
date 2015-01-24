"""
Copyright (c) 2014+, Anthony Garcia <anthony@lagg.me>
Distributed under the ISC License. See README
"""

from urllib.parse import urlencode, urlparse, parse_qs
from urllib.request import urlopen, Request
from urllib.error import URLError
import re
import operator
import logging
import unicodedata
import json

import steam
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class ScraperError(Exception):
    def __init__(self, game):
        super(ScraperError, self).__init__(u"{0[name]}: Times not found".format(game))

class TimesNotFound(ScraperError):
    pass

class SteamTimesNotFound(TimesNotFound):
    pass

class HLTBTimesNotFound(TimesNotFound):
    pass

class scraper(object):
    """ Base class for filthy ugly scrapers. Not very documented because
    extreme guilt and such.
    """

    # Mapping of the unicode fractional chars (one-half, one-quarter, etc.)
    # to sane values
    _fractional_chars = {
            u'\xbc': 0.25,
            u'\xbd': 0.50,
            u'\xbe': 0.75
            }

    # Yes I know it's bad. I know.
    _char_name_exp = re.compile(r"LATIN (SMALL|CAPITAL) LETTER ([A-Za-z0-9]+) ?")

    # Extra HTTP headers. Shouldn't change for two reasons: 1) Some websites look for non-"standard" UA
    # strings. 2) Scraping isn't very nice. I'm kind of treading the line due to desperation but they
    # at least deserve to be given decent warning.
    _http_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:33.0) Gecko/20100101 Firefox/33.0",
            "X-Fetched-By": "Backlagg.steamhtlb. Please forgive the scraping."
            }

    def _clean_game_name(self, name):
        """ Cleans up the given name so that it's more likely to show up in search results """
        # The replace calls are to strip trademark symbols and other stuff that interferes with searches
        cleanedname = name.replace(u"\xae", '').replace(u"\u2122", '').replace(": ", ' ').replace("'", '').replace(" - ", ' ')

        # What is about to occur here may be frightening. It is. But not moreso than
        # writing one's own hardcoded translation tables *shiver*
        chars = list(cleanedname)
        for i in range(len(chars)):
            c = chars[i]

            try:
                asciichar = c.encode("ascii")
            except UnicodeEncodeError:
                charname = unicodedata.name(c)
                matches = self._char_name_exp.search(charname)

                if matches:
                    newchar = matches.group(2)
                    if matches.group(1) == "SMALL":
                        newchar = newchar.lower()
                    chars[i] = newchar
                else:
                    logger.debug(u"Non-ascii char {0} ({1}) couldn't be converted".format(c, charname))

        cleanedname = ''.join(chars)

        return cleanedname


class hltb(scraper):
    """ Given a dict as returned by user_hours' iterator
    tries to lookup the game on HLTB using a combination of
    heuristics and disgusting hax to make it as accurate as possible
    and builds a merged summary of hours from there and the user's own.
    """

    # The URL to POST the game name query to. Could yield better or at least different
    # results if the params were fiddled with. Let me know if you find anything good.
    _name_search_url = "http://www.howlongtobeat.com/search_main.php?t=games&page=1&sorthead=popular&sortd=Normal%20Order&plat=&detail=0"

    # The regexp that gets ran on the area that looks like the hours are at.
    _hours_exp = re.compile(r"([0-9]+)([^0-9]*) Hours")

    def __init__(self, game, retries=3):
        """ game: game dict as returned by user_hours iteration
        retries: number of times to shorten and retry a name search
        """
        self._game = game
        self._retries = max(1, retries)

    def _fetch_soup(self, name):
        """ I feel like a bit of an asshole for doing this, hence the guilty header. Sorry :( """
        query = urlencode({"queryString": name.encode("utf-8")}).encode("ascii")

        try:
            playtimes_request = Request(self._name_search_url, query, self._http_headers)
            playtimes = urlopen(playtimes_request)
            return BeautifulSoup(playtimes.read())
        except URLError:
            logger.error(u"HLTB connection error: {0[name]}".format(self._game))
            return None

    def fetch(self):
        querystring = self._clean_game_name(self._game["name"])

        matches = []
        result = {"hours": {}}
        retries = 0

        while len(matches) == 0 and retries < self._retries:
            result["final_name"] = querystring
            soup = self._fetch_soup(querystring)

            if not soup:
                raise HLTBTimesNotFound(self._game)

            matches = soup.findAll(class_="gamelist_details")

            if len(matches) > 0:
                found_name = None

                if retries > 0:
                    found_name_href = matches[0].select("h3 a")

                    if found_name_href:
                        found_name = found_name_href[0].text
                    else:
                        found_name = '?'

                    logger.warn(u"{0[name]} ({0[appid]}) was found but only after shortening name to '{1}' giving '{2}'".format(self._game, querystring, found_name))
                    result["partial_match"] = True
                elif found_name and found_name.lower() != querystring.lower():
                    logger.warn(u"{0[name]} was apparently found but the search and names differ. '{1}' versus '{2}'".format(self._game, querystring, found_name))

                break
            else:
                retries += 1
                # This is what I call ^W simulation
                splitqs = querystring.rsplit(' ', 1)
                if len(splitqs) < 2:
                    break

                querystring = splitqs[0].strip(':')

        if len(matches) > 0:
            match = matches[0]
            tidbits = match.findAll("div", class_="gamelist_tidbit")
            last_tidbit_type = None

            for tidbit in tidbits:
                tidbit_match = self._hours_exp.search(tidbit.text)
                if tidbit_match:
                    hrsrounded = float(tidbit_match.group(1))
                    fractional = tidbit_match.group(2)

                    if fractional:
                        hrsrounded += self._fractional_chars.get(fractional, 0)

                    # Should never already exist, if it does there's a bug
                    assert (last_tidbit_type and last_tidbit_type not in result["hours"])

                    time_accuracy = 0
                    # There is apparently an accuracy rating on HLTB. Useful.
                    for cls in tidbit["class"]:
                        if cls.startswith("time_"):
                            time_accuracy = int(cls[5:])
                            break

                    result["hours"][last_tidbit_type] = {"time": hrsrounded, "accuracy": time_accuracy}
                elif ' '.join(tidbit["class"]).find("time_") == -1:
                    last_tidbit_type = tidbit.text

        if not result["hours"]:
            logger.warn(u"HLTB: {0[name]} ({0[appid]}): No times found".format(self._game))
            raise HLTBTimesNotFound(self._game)
        else:
            logger.debug(u"HLTB: {0[name]} ({0[appid]}): {1}".format(self._game,
                ', '.join(["{0}: {1} ({2})".format(tidbit, hrs["time"], hrs["accuracy"])
                           for tidbit, hrs in sorted(result["hours"].items(),
                           key=lambda x: (x[1]["accuracy"], x[1]["time"]), reverse=True)])))

        return result


class review_times(scraper):
    """ Experimental thingy that can be used as a fallback
    if hltb doesn't work. Searches the top few most helpful steam reviews for the given game
    for their own hours. The average might be somewhat helpful assuming the
    top reviews aren't written by the mouthbreathing nitwits that do "huehue 10/10"
    humor abortions and thumbed up by other mouthbreathing nitwits.
    """

    # The URL to search for the reviews. Note the format token that the appid gets inserted at
    _reviews_url = "http://steamcommunity.com/app/{0}/homecontent/?appHubSubSection=10&l=english&browsefilter=toprated&filterLanguage=default"

    # The regexp that gets ran on text content of the general area the hours should be at.
    # shouldn't need to be messed with unless Valve messes with layout a lot.
    _hours_exp = re.compile(r"(\d+\.\d+) hrs on record")

    def __init__(self, game, pages=1):
        """ game: game dict a returned by the user_hours iterable
        pages: how many pages of reviews to fetch. More pages mean more accurate times, but more pages requests and possibly more load and a throttling """

        self._game = game
        self._hours = {}
        self._pages = max(1, pages)

    def _fetch_soup(self, last_soup=None):
        """ Fetches the next page of  soup from the steam reviews.
        last_soup: The previous soup returned, will be used to fetch the next page """

        url_suffix = ''

        if last_soup:
            pageform = last_soup.find("form")

            if pageform:
                nextpage_params = []

                for tag in pageform.findAll(attrs={"type": "hidden"}):
                    nextpage_params.append(urlencode({tag["name"]: tag["value"]}))

                if nextpage_params:
                    url_suffix = "&" + "&".join(nextpage_params)

        try:
            url = self._reviews_url.format(self._game["appid"]) + url_suffix
            #logger.debug("Fetching steam review page: " + url)
            req = Request(url, None, self._http_headers)
            times = urlopen(req)
        except URLError:
            logger.error(u"Steam review page connection error: {0[name]}".format(self._game))
            raise SteamTimesNotFound(self._game)

        soup = BeautifulSoup(times.read())

        return soup

    def fetch(self):
        self._hours = {}
        hours = []
        soup = None

        for i in range(self._pages):
            soup = self._fetch_soup(last_soup=soup)

            cards = soup.findAll(class_="apphub_Card")

            for card in cards:
                hr = card.find(class_="hours")
                title = card.find(class_="title")

                if not hr or not title:
                    logger.warn(u"Couldn't find hour/title set for {0[name]}. Layout may have changed.".format(self._game))
                    raise SteamTimesNotFound(self._game)

                hrmatch = self._hours_exp.search(hr.text)
                titletext = title.text.strip()

                # Check for only recommended since those are
                # usually the ones with the most accurate hours for
                # obvious reasons
                if hrmatch and titletext == "Recommended":
                    hours.append(float(hrmatch.group(1)))

        self._hours = {"hours": hours, "average": round(float(sum(hours)) / len(hours), 2)}

        if hours:
            logger.debug(u"Steam reviews: {0[name]} ({0[appid]}): {1} times scraped with an average of {2:0.2f} hrs.".format(self._game, len(hours), self._hours["average"]))
        else:
            logger.warn(u"Steam reviews: {0[name]} ({0[appid]}): No times found".format(self._game))

        return self._hours


class storefront_metadata(scraper):
    """ Implements a scraper that grabs stuff from game storefront pages
    such as categories and tags that otherwise aren't available via API.
    """
    _store_url = "http://store.steampowered.com/app/{0}"
    _tag_exp = re.compile(r"InitAppTagModal\([0-9\s]+,\s*(\[{.+}\])")

    def __init__(self, game):
        self._game = game
        self._store_page = None

    @property
    def categories(self):
        """ Fetch categories for the game. These are different from tags. They're
        the things in the lower sidebar that say things like "Full controller support" or
        "Steam trading cards"
        """
        if not self._store_page and not self.fetch():
            return None

        categories = self._store_page.find("div", attrs={"id": "category_block"})

        if categories:
            cats = []
            entries = categories.findAll("div", class_="game_area_details_specs")

            for entry in entries:
                cat = entry.find("a", class_="name")

                try:
                    categoryid = parse_qs(urlparse(cat["href"]).query).get("category2", [0])[0]
                except KeyError:
                    continue

                cats.append({"name": cat.text, "catid": int(categoryid)})

            return cats

    def fetch(self):
        try:
            req = Request(self._store_url.format(self._game["appid"]), None, self._http_headers)
            self._store_page = BeautifulSoup(urlopen(req).read())
            return self._store_page
        except URLError as e:
            logger.error(u"Steam storefront connection error ({1}): {0[name]}".format(self._game, e))
            return None

    @property
    def tags(self):
        """ Fetch tags for the game """
        # I find it thoroughly amusing that valve has json feeds for other tag related stuff including POSTing new ones, but not getting the set of tags for a given game
        if not self._store_page and not self.fetch():
            return None

        scripts = self._store_page.findAll("script", attrs={"type": "text/javascript"})

        for script in scripts:
            matches = self._tag_exp.search(script.text)

            if matches:
                return json.loads(matches.group(1))


class user_hours(object):
    """ An iterable that fetches hours
    (and associated game info) for a given
    user to be passed to hltb
    """

    def __init__(self, user):
        """ user: An id64 or steam.user-like object """

        self._steam_hours = None
        self._owned_game_count = 0

        try:
            self._id64 = user.id64
        except AttributeError:
            try:
                self._id64 = int(user)
            except ValueError:
                self._id64 = steam.user.vanity_url(user).id64

    def __iter__(self):
        return next(self)

    def __len__(self):
        if not self._steam_hours:
            self.fetch()

        return self._owned_game_count

    def __next__(self):
        """ Yields the next game dict """
        if not self._steam_hours:
            self.fetch()

        for game in self._steam_hours:
            yield game
    next =  __next__

    def fetch(self):
        """ Pull the user hours/game list, returns entire sorted result list with times converted to hours """
        self._steam_hours = sorted(steam.api.interface("IPlayerService").GetOwnedGames(steamid=self._id64,
                                   include_appinfo=1, include_played_free_games=1)["response"]["games"],
                                   key=operator.itemgetter("playtime_forever"))
        self._owned_game_count = len(self._steam_hours)

        for game in self._steam_hours:
            try:
                game["playtime_forever"] = float(game["playtime_forever"]) / 60
            except KeyError:
                pass

            try:
                game["playtime_2weeks"] = float(game["playtime_2weeks"]) / 60
            except KeyError:
                pass

        return self._steam_hours

class steam_achievements(object):
    def __init__(self, game):
        self._game = game
        self._achievements = None

    def __iter__(self):
        return next(self)

    def __next__(self):
        if not self._achievements:
            self.fetch()

        for achievement in self._achievements:
            yield achievement
    next = __next__

    def fetch(self):
        achievements = steam.api.interface("ISteamUserStats").GetGlobalAchievementPercentagesForApp(version=2, gameid=self._game["appid"])

        try:
            self._achievements = achievements["achivementpercentages"]["achievements"]
            return self._achievements
        except KeyError:
            return None
