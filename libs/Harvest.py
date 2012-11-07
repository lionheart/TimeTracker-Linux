import urllib2
from urllib import urlencode
from base64 import b64encode
from dateutil.parser import parse as parseDate

import json
from StringIO import StringIO

class HarvestError(Exception):
    pass

class Harvest(object):
    def __init__(self, uri, email, password):
        self.uri = uri
        self.headers = {
            'Authorization': 'Basic ' + b64encode('%s:%s' % (email, password)),
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'TimeTracker for Linux',
        }

    def status(self):
        return self._request("GET", 'http://harveststatus.com/status.json')

    def get_today(self):
        return self._request('GET', "%s/daily"%self.uri)

    def get_day(self, day_of_the_year=1, year=2012):
        return self._request('GET', '%s/daily/%s/%s' % (self.uri, day_of_the_year, year))

    def get_entry(self, entry_id):
        return self._request("GET", "%s/daily/show/%s"%(self.uri, entry_id))

    def toggle_timer(self, entry_id):
        return self._request("GET", "%s/daily/timer/%s" %(self.uri, entry_id))

    def add(self, data):
        return self._request("POST", '%s/daily/add' % self.uri, data)

    def delete(self, entry_id):
        return self._request("DELETE", "%s/daily/delete/%s" % (self.uri, entry_id))

    def update(self, entry_id, data):
        return self._request('POST', '%s/daily/update/%s'% (self.uri, entry_id), urlencode(data))

    def _request(self, type = "GET", url = "", data = None ):
        """
        type = request type, eg. GET, POST, DELETE
        url = full url to make request to, eg. https://MYCOMPANY.harvestapp.com/daily
        data = data for the request, leave empty for get requests

        """
        if type != "DELETE":
            if data:
                request = urllib2.Request(url=url, data=data, headers=self.headers)
                print data
            else:
                request = urllib2.Request(url=url, headers=self.headers)

            try:
                r = urllib2.urlopen(request)
                j = r.read()
                j = StringIO(j)
                return json.load(j)
            except Exception as e:
                raise HarvestError(e)
        else:
            try:
                opener = urllib2.build_opener(urllib2.HTTPHandler)
                request = urllib2.Request(url=url, headers=self.headers)
                request.get_method = lambda: "DELETE"
                return opener.open(request)
            except Exception as e:
                raise HarvestError(e)
