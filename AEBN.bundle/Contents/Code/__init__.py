#!/usr/bin/env python
# encoding=utf8
'''
# AEBN - (IAFD)
                                                  Version History
                                                  ---------------
    Date            Version                         Modification
    19 Aug 2022     2020.05.21.13   Multiple Improvements and major rewrites
                                    - tidy up of genres as they have different names across various websites.
                                    - tidy up of countries and locations
                                    - introduced Grouped Collections and Default to keep track of films
    27 Nov 2022     2020.05.21.14   Updated to use latest version of utils.py
    04 Dec 2022     2020.05.21.15   Renamed to AEBN

-----------------------------------------------------------------------------------------------------------------------------------
'''
import copy, json, re
from datetime import datetime

# Version / Log Title
VERSION_NO = '2020.05.21.15'
AGENT = 'AEBN'
AGENT_TYPE = '⚣'   # '⚤' if straight agent

# URLS
BASE_URL = 'https://gay.aebn.com'
BASE_SEARCH_URL = BASE_URL + '/gay/search?queryType=Free+Form&sysQuery={0}&criteria=%7B%22sort%22%3A%22Relevance%22%7D'
WATERMARK = 'https://cdn0.iconfinder.com/data/icons/mobile-device/512/lowcase-letter-d-latin-alphabet-keyboard-2-32.png'

# Date Formats used by website
DATEFORMAT = '%b %d, %Y'

# Website Language
SITE_LANGUAGE = 'en'

# Preferences
MATCHSITEDURATION = ''

# dictionaries & Set for holding film variables, genres and countries
FILMDICT = {}

# utils.log section separators
LOG_BIGLINE = '-' * 140
LOG_SUBLINE = '      ' + '-' * 100
LOG_ASTLINE = '*' * 140
# ----------------------------------------------------------------------------------------------------------------------------------
# imports placed here to use previously declared variables
import utils

# ----------------------------------------------------------------------------------------------------------------------------------
def Start():
    ''' initialise process '''
    HTTP.CacheTime = CACHE_1WEEK
    HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.102 Safari/537.36 Edg/104.0.1293.63'

    utils.setupStartVariables()
    ValidatePrefs()

# ----------------------------------------------------------------------------------------------------------------------------------
def ValidatePrefs():
    ''' Validate Changed Preferences '''
    pass

# ----------------------------------------------------------------------------------------------------------------------------------
class AEBN(Agent.Movies):
    ''' define Agent class '''
    name = 'AEBN (IAFD)'
    languages = [Locale.Language.English]
    primary_provider = False
    preference = True
    media_types = ['Movie']
    contributes_to = ['com.plexapp.agents.GayAdult', 'com.plexapp.agents.GayAdultFilms']

    # -------------------------------------------------------------------------------------------------------------------------------
    def CleanSearchString(self, myString):
        ''' Prepare Title for search query '''
        utils.log('AGENT :: {0:<29} {1}'.format('Original Search Query', myString))

        # convert to lower case and trim and strip diacritics, fullstops, enquote
        myString = myString.lower().strip()
        myString = String.StripDiacritics(myString)

        # sort out double encoding: & html code %26 for example is encoded as %2526; on MAC OS '*' sometimes appear in the encoded string
        myString = String.URLEncode('{0}'.format(myString)).replace('%25', '%').replace('*', '')

        utils.log('AGENT :: {0:<29} {1}'.format('Returned Search Query', myString))
        utils.log(LOG_BIGLINE)

        return myString

    # -------------------------------------------------------------------------------------------------------------------------------
    def search(self, results, media, lang, manual):
        ''' Search For Media Entry '''
        if not media.items[0].parts[0].file:
            utils.log(LOG_ASTLINE)
            utils.log('SEARCH:: {0:<29} {1}'.format('Error: Missing Media Item File', 'QUIT'))
            utils.log(LOG_ASTLINE)
            return

        #clear-cache directive
        if media.name == "clear-cache":
            HTTP.ClearCache()
            results.Append(MetadataSearchResult(id='clear-cache', name='Plex web cache cleared', year=media.year, lang=lang, score=0))
            utils.log(LOG_ASTLINE)
            utils.log('SEARCH:: {0:<29} {1}'.format('Warning: Clear Cache Directive Encountered', 'QUIT'))
            utils.log(LOG_ASTLINE)
            return

        utils.logHeader('SEARCH', media, lang)

        # Check filename format
        try:
            FILMDICT = copy.deepcopy(utils.matchFilename(media))
            FILMDICT['lang'] = lang
            FILMDICT['Agent'] = AGENT
            FILMDICT['Status'] = False
        except Exception as e:
            utils.log(LOG_ASTLINE)
            utils.log('SEARCH:: Error: %s', e)
            utils.log(LOG_ASTLINE)
            return

        utils.log(LOG_BIGLINE)

        # Search Query - for use to search the internet, remove all non alphabetic characters.
        # if title is in a series the search string will be composed of the Film Title minus Series Name and No.
        for searchTitle in FILMDICT['SearchTitles']:
            if FILMDICT['Status'] is True:
                break

            searchTitle = self.CleanSearchString(searchTitle)
            searchQuery = BASE_SEARCH_URL.format(searchTitle)
            morePages = True
            pageNumber = 0
            while morePages:
                utils.log('SEARCH:: {0:<29} {1}'.format('Search Query', searchQuery))
                pageNumber += 1
                if pageNumber > 10:
                    morePages = False     # search a maximum of 10 pages
                    utils.log('SEARCH:: Warning: Page Search Limit Reached [10]')
                    continue

                try:
                    html = HTML.ElementFromURL(searchQuery, timeout=20, sleep=utils.delay())
                    filmsList = html.xpath('//div[@class="dts-collection-item dts-collection-item-movie"][@id]/div[contains(@id, "dtsImageOverlayContainer")]')
                    if not filmsList:
                        raise Exception('< No Films! >')

                    # if there is a list of films - check if there are further pages returned
                    try:
                        searchQuery = html.xpath('//ul[@class="dts-pagination"]/li[@class="active" and text()!="..."]/following::li/a[@class="dts-paginator-tagging"]/@href')[0]
                        searchQuery = (BASE_URL if BASE_URL not in searchQuery else '') + searchQuery
                        morePages = True    # next page search query determined so set as true
                    except:
                        morePages = False

                except Exception as e:
                    utils.log('SEARCH:: Error: Search Query did not pull any results: %s', e)
                    break

                filmsFound = len(filmsList)
                utils.log('SEARCH:: {0:<29} {1}'.format('Titles Found', '{0} Processing Results Page: {1:>2}'.format(filmsFound, pageNumber)))
                utils.log(LOG_BIGLINE)
                myYear = '({0})'.format(FILMDICT['Year']) if FILMDICT['Year'] else ''
                for idx, film in enumerate(filmsList, start=1):
                    utils.log('SEARCH:: {0:<29} {1}'.format('Processing', 'Page {0}: {1} of {2} for {3} - {4} {5}'.format(pageNumber, idx, filmsFound, FILMDICT['Studio'], FILMDICT['Title'], myYear)))
                    utils.log(LOG_BIGLINE)

                    # Site Title
                    try:
                        filmTitle = film.xpath('./a[contains(@href,"/movies/")]//img/@title')[0]
                        utils.matchTitle(filmTitle, FILMDICT)
                    except Exception as e:
                        utils.log('SEARCH:: Error getting Site Title: %s', e)
                        utils.log(LOG_SUBLINE)
                        continue

                    # Site Title URL
                    utils.log(LOG_BIGLINE)
                    try:
                        filmURL = film.xpath('./a/@href')[0]
                        filmURL = ('' if BASE_URL in filmURL else BASE_URL) + filmURL
                        FILMDICT['FilmURL'] = filmURL
                        utils.log('SEARCH:: {0:<29} {1}'.format('Site Title URL', filmURL))
                    except:
                        utils.log('SEARCH:: Error getting Site Title Url')
                        utils.log(LOG_SUBLINE)
                        continue

                    # Access Site URL for Studio and Release Date information
                    utils.log(LOG_BIGLINE)
                    try:
                        utils.log('SEARCH:: {0:<29} {1}'.format('Reading Site URL page', filmURL))
                        fhtml = HTML.ElementFromURL(FILMDICT['FilmURL'], sleep=utils.delay())
                        FILMDICT['FilmHTML'] = fhtml
                    except Exception as e:
                        utils.log('SEARCH:: Error reading Site URL page: %s', e)
                        utils.log(LOG_SUBLINE)
                        continue

                    # Site Studio Name
                    utils.log(LOG_BIGLINE)
                    matchedStudio = False
                    try:
                        fhtmlStudios = fhtml.xpath('//div[@class="dts-studio-name-wrapper"]/a/text()')
                        utils.log('UPDATE:: {0:<29} {1}'.format('Site URL Studios', '{0:>2} - {1}'.format(len(fhtmlStudios), fhtmlStudios)))
                        for item in fhtmlStudios:
                            try:
                                utils.matchStudio(item, FILMDICT)
                                matchedStudio = True
                                break
                            except Exception as e:
                                utils.log('SEARCH:: Error Matching %s: %s', item, e)
                    except Exception as e:
                        utils.log('SEARCH:: Error getting Site Studio %s', e)

                    if not matchedStudio:
                        utils.log('SEARCH:: Error No Matching Site Studio')
                        utils.log(LOG_SUBLINE)
                        continue

                    # Site Release Date
                    utils.log(LOG_BIGLINE)
                    vReleaseDate = FILMDICT['CompareDate']
                    try:
                        fhtmlReleaseDate = fhtml.xpath('//li[contains(@class,"item-release-date")]/text()')[0].strip()
                        fhtmlReleaseDate = fhtmlReleaseDate.replace('July', 'Jul').replace('Sept', 'Sep')    # AEBN uses 4 letter abbreviation for September & July
                        utils.log('SEARCH:: {0:<29} {1}'.format('Site URL Release Date', fhtmlReleaseDate))
                        try:
                            releaseDate = datetime.strptime(fhtmlReleaseDate, DATEFORMAT)
                            utils.matchReleaseDate(releaseDate, FILMDICT)
                            vReleaseDate = releaseDate
                        except Exception as e:
                            utils.log('SEARCH:: Error getting Site URL Release Date: %s', e)
                            if FILMDICT['Year']:
                                utils.log(LOG_SUBLINE)
                                continue
                    except:
                        utils.log('SEARCH:: Error getting Site URL Release Date: Default to Filename Date')

                    # Site Film Duration
                    utils.log(LOG_BIGLINE)
                    matchedDuration = False
                    vDuration = FILMDICT['Duration']
                    try:
                        fhtmlDuration = fhtml.xpath('//span[text()="Running Time:"]/parent::li/text()')[0].strip()
                        utils.log('SEARCH:: {0:<29} {1}'.format('Site Film Duration', fhtmlDuration))
                        fhtmlDuration = fhtmlDuration.split(':')                                                      # split into hr, mins, secs
                        fhtmlDuration = [int(x) for x in fhtmlDuration]                                               # convert to integer
                        fhtmlDuration = ['0{0}'.format(x) if x < 10 else '{0}'.format(x) for x in fhtmlDuration]      # converted to zero padded items
                        fhtmlDuration = ['00'] + fhtmlDuration if len(fhtmlDuration) == 2 else fhtmlDuration    # prefix with zero hours if string is only minutes and seconds
                        fhtmlDuration = '1970-01-01 {0}'.format(':'.join(fhtmlDuration))                              # prefix with 1970-01-01 to conform to timestamp
                        duration = datetime.strptime(fhtmlDuration, '%Y-%m-%d %H:%M:%S')                                 # turn to date time object
                        try:
                            utils.matchDuration(duration, FILMDICT)
                            matchedDuration = True
                            vDuration = duration
                        except Exception as e:
                            utils.log('SEARCH:: Error matching Site Film Duration: %s', e)
                    except Exception as e:
                        utils.log('SEARCH:: Error getting Site Film Duration')

                    if MATCHSITEDURATION and not matchedDuration:
                        utils.log(LOG_SUBLINE)
                        continue

                    FILMDICT['vCompilation'] = ''
                    FILMDICT['vDuration'] = vDuration
                    FILMDICT['vReleaseDate'] = vReleaseDate
                    del FILMDICT['FilmHTML']

                    myID = json.dumps(FILMDICT, default=utils.jsonDumper)
                    results.Append(MetadataSearchResult(id=myID, name=FILMDICT['Title'], score=100, lang=lang))

                    # Film Scraped Sucessfully - update status and break out!
                    FILMDICT['Status'] = True
                    break       # stop processing

                if FILMDICT['Status'] is True:      # if search and process sucessful stop processing
                    break

        # End Search Routine
        utils.logFooter('SEARCH', FILMDICT)
        return FILMDICT['Status']

    # -------------------------------------------------------------------------------------------------------------------------------
    def update(self, metadata, media, lang, force=True):
        ''' Update Media Entry '''
        utils.logHeader('UPDATE', media, lang)

        utils.log('UPDATE:: Convert Date Time & Set Objects:')
        FILMDICT = json.loads(metadata.id, object_hook=utils.jsonLoader)
        utils.log(LOG_BIGLINE)

        utils.printFilmInformation(FILMDICT)

        FILMDICT['Status'] = True

        # use general routine to get Metadata
        utils.log(LOG_BIGLINE)
        try:
            utils.log('SEARCH:: Access Site URL Link:')
            fhtml = HTML.ElementFromURL(FILMDICT['FilmURL'], sleep=utils.delay())
            FILMDICT['FilmHTML'] = fhtml
            FILMDICT[AGENT] = utils.getSiteInfo(AGENT, FILMDICT, kwCompilation=FILMDICT['vCompilation'], kwReleaseDate=FILMDICT['vReleaseDate'], kwDuration=FILMDICT['vDuration'])

        except Exception as e:
            utils.log('SEARCH:: Error Accessing Site URL page: %s', e)
            FILMDICT['Status'] = False

        # we should have a match on studio, title and year now. Find corresponding film on IAFD
        utils.log(LOG_BIGLINE)
        try:
            utils.log(LOG_BIGLINE)
            utils.log('SEARCH:: Check for Film on IAFD:')
            utils.getFilmOnIAFD(FILMDICT)

        except:
            pass

        # update the metadata
        utils.log(LOG_BIGLINE)
        if FILMDICT['Status'] is True:
            utils.log(LOG_BIGLINE)
            '''
            The following bits of metadata need to be established and used to update the movie on plex
            1.  Metadata that is set by Agent as default
                a. id.                 : Plex media id setting
                b. Studio              : From studio group of filename - no need to process this as above
                c. Title               : From title group of filename - no need to process this as is used to find it on website
                d. Tag line            : Corresponds to the url of film
                e. Originally Available: set from metadata.id (search result)
                f. Content Rating      : Always X
                g. Content Rating Age  : Always 18

            2.  Metadata retrieved from website
                a. Originally Availiable Date
                b. Ratings
                c. Genres                           : List of Genres (alphabetic order)
                d. Countries
                e. Cast                             : List of Actors and Photos (alphabetic order) - Photos sourced from IAFD
                f. Directors                        : List of Directors (alphabetic order)
                g. Collections                      : retrieved from FILMDICT, Genres, Countries, Cast Directors
                h. Posters
                i. Art (Background)
                j. Reviews
                k. Chapters
                l. Summary
            '''
            utils.setMetadata(metadata, media, FILMDICT)

        # Failure: initialise original availiable date, so that one can find titles sorted by release date which are not scraped
        if FILMDICT['Status'] is False:
            metadata.originally_available_at = None
            metadata.year = 0

        utils.logFooter('UPDATE', FILMDICT)
        return FILMDICT['Status']