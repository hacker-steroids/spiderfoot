#-------------------------------------------------------------------------------
# Name:        sfp_gravatar
# Purpose:     SpiderFoot plug-in to search Gravatar API for an email address
#              and retrieve user information, including username, name, phone
#              numbers, additional email addresses, and social media usernames.
#
# Author:      <bcoles@gmail.com>
#
# Created:     2019-05-26
# Copyright:   (c) bcoles 2019
# Licence:     GPL
#-------------------------------------------------------------------------------

import json
import hashlib
import re
import time
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

class sfp_gravatar(SpiderFootPlugin):
    """Gravatar:Footprint,Investigate,Passive:Social Media::Retrieve user information from Gravatar API."""

    # Default options
    opts = {
    }

    # Option descriptions
    optdescs = {
    }

    results = dict()

    def setup(self, sfc, userOpts=dict()):
        self.sf = sfc
        self.__dataSource__ = 'Gravatar'
        self.results = dict()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return ['EMAILADDR']

    # What events this module produces
    def producedEvents(self):
        return ['RAW_RIR_DATA', 'HUMAN_NAME', 'USERNAME', 'EMAILADDR', 'PHONE_NUMBER', 'GEOINFO']

    # Query Gravatar API for the specified email address
    # https://secure.gravatar.com/site/implement/
    # https://secure.gravatar.com/site/implement/profiles/
    def query(self, qry):
        email_hash = hashlib.md5(qry.encode('utf-8').lower()).hexdigest()
        output = 'json'

        res = self.sf.fetchUrl("https://secure.gravatar.com/" + email_hash + '.' + output,
                               timeout=self.opts['_fetchtimeout'],
                               useragent=self.opts['_useragent'])

        time.sleep(1)

        if res['content'] is None:
            self.sf.debug('No response from gravatar.com')
            return None

        if res['code'] != '200':
            return None

        try:
            data = json.loads(res['content'])
        except BaseException as e:
            self.sf.debug('Error processing JSON response: ' + str(e))
            return None

        if data.get('entry') is None or len(data.get('entry')) == 0:
            return None

        return data.get('entry')[0]

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data

        if eventData in self.results:
            return None

        self.results[eventData] = True

        self.sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        data = self.query(eventData)

        if data is None:
            self.sf.debug("No user information found for " + eventData)
            return None

        evt = SpiderFootEvent("RAW_RIR_DATA", str(data), self.__name__, event)
        self.notifyListeners(evt)

        if data.get('preferredUsername') is not None:
            evt = SpiderFootEvent("USERNAME", data.get('preferredUsername'), self.__name__, event)
            self.notifyListeners(evt)

        if data.get('name') is not None and data.get('name').get('formatted') is not None:
            evt = SpiderFootEvent("HUMAN_NAME", data.get('name').get('formatted'), self.__name__, event)
            self.notifyListeners(evt)

        # location can not be trusted
        #if data.get('currentLocation') is not None:
        #    location = data.get('currentLocation')
        #    if len(location) < 3 or len(location) > 100:
        #        self.sf.debug("Skipping likely invalid location.")
        #    else:
        #        evt = SpiderFootEvent("GEOINFO", location, self.__name__, event)
        #        self.notifyListeners(evt)

        if data.get('phoneNumbers') is not None:
            for number in data.get('phoneNumbers'):
                if number.get('value') is not None:
                    evt = SpiderFootEvent("PHONE_NUMBER", number.get('value'), self.__name__, event)
                    self.notifyListeners(evt)

        if data.get('emails') is not None:
            for email in data.get('emails'):
                if email.get('value') is not None:
                    evt = SpiderFootEvent("EMAILADDR", email.get('value'), self.__name__, event)
                    self.notifyListeners(evt)

        if data.get('ims') is not None:
            for im in data.get('ims'):
                if im.get('value') is not None:
                    evt = SpiderFootEvent("USERNAME", im.get('value'), self.__name__, event)
                    self.notifyListeners(evt)

        if data.get('accounts') is not None:
            for account in data.get('accounts'):
                if account.get('username') is not None:
                    evt = SpiderFootEvent("USERNAME", account.get('username'), self.__name__, event)
                    self.notifyListeners(evt)

# End of sfp_gravatar class
