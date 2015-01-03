"""
Copyright (c) 2014+, Anthony Garcia <anthony@lagg.me>
Distributed under the ISC License. See README
"""

import urllib2
from urllib import urlencode
import re
import operator
# TODO: Use proper logger creator
import logging
import unicodedata

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
        # The replace calls are to strip trademark symbols.
        cleanedname = name.replace(u"\xae", '').replace(u"\u2122", '')

        # What is about to occur here may be frightening. It is. But not moreso than
        # writing one's own hardcoded translation tables *shiver*
        chars = list(cleanedname)
        for i in range(len(chars)):
            c = chars[i]

            try:
                asciichar = c.encode("ascii")
            except UnicodeEncodeError:
                charname = unicodedata.name(c)
                matches = _char_name_exp.search(charname)

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
        self._retries = retries

    def _fetch_soup(self, name):
        """ I feel like a bit of an asshole for doing this, hence the guilty header. Sorry :( """
        query = urlencode({"queryString": name.encode("utf-8")})

        try:
            playtimes_request = urllib2.Request(self._name_search_url, query, self._http_headers)
            playtimes = urllib2.urlopen(playtimes_request)
            return BeautifulSoup(playtimes.read())
        except urllib2.URLError:
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
                if retries > 0:
                    found_name_href = matches[0].select("h3 a")

                    if found_name_href:
                        found_name = found_name_href[0].text
                    else:
                        found_name = '?'

                    logger.warn(u"{0[name]} ({0[appid]}) was found but only after shortening name to '{1}' giving '{2}'".format(self._game, querystring, found_name))
                    result["partial_match"] = True
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

                    # Convert to minutes for consistency with steam
                    result["hours"][last_tidbit_type] = {"time": hrsrounded * 60, "accuracy": time_accuracy}
                elif ' '.join(tidbit["class"]).find("time_") == -1:
                    last_tidbit_type = tidbit.text

        if not result["hours"]:
            logger.warn(u"Times not found: {0[name]} ({0[appid]}) ({1:.2f} hrs)".format(self._game, float(self._game["playtime_forever"]) / 60))
            raise HLTBTimesNotFound(self._game)
        else:
            logger.debug(u"{0[name]} ({0[appid]}): {1}".format(self._game, ', '.join(sorted(["{0}: {1} ({2})".format(tidbit, hrs["time"] / 60, hrs["accuracy"]) for tidbit, hrs in result["hours"].items()]))))

        return result


class review_times(scraper):
    """ Experimental thingy that can be used as a fallback
    if hltb doesn't work. Not used in backlog proper but might be of some
    use. Searches the top few most helpful steam reviews for the given game
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
        self._pages = pages

    def fetch(self):
        self._hours = {}

        try:
            req = urllib2.Request(self._reviews_url.format(self._game["appid"]), None, self._http_headers)
            times = urllib2.urlopen(req)
        except urllib2.URLError:
            logger.error(u"Steam review page connection error: {0[name]}".format(self._game))
            raise SteamTimesNotFound(self._game)

        soup = BeautifulSoup(times.read())
        cards = soup.findAll(class_="apphub_Card")
        hours = []

        # TODO: Make this do something to emulate the infinite scroll
        pageform = soup.find("form")
        nextpage_params = []
        for tag in pageform.findAll(attrs={"type": "hidden"}):
            nextpage_params.append(urlencode({tag["name"]: tag["value"]}))
        nextpage_params = '?' + "&".join(nextpage_params)

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

        self._hours = {"hours": hours, "average": sum(hours) / len(hours)}

        return self._hours


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
        """ Pull the user hours/game list, returns entire sorted result list """
        self._steam_hours = sorted(steam.api.interface("IPlayerService").GetOwnedGames(steamid=self._id64,
                                   include_appinfo=1, include_played_free_games=1)["response"]["games"],
                                   key=operator.itemgetter("playtime_forever"))
        self._owned_game_count = len(self._steam_hours)

        return self._steam_hours
