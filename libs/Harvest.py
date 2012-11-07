'''
>>> import Harvest
>>> harvest = Harvest.Harvest("https://COMPANYNAME.harvestapp.com", "EMAIL", "PASSWORD")
>>> harvest.status()[""]
>>> data = {"notes":"test note", "project_id":"PROJECT_ID","hours":"1.0", "task_id": "TASK_ID"}
>>> harvest.add(data)
>>> data['notes'] = "another test"
>>> harvest.update("ENTRY_ID", data)
>>> harvest.get_today()

'''
import urllib2
from urllib import urlencode
from base64 import b64encode

import json
from StringIO import StringIO #to parse json

from xml.dom.minidom import Document #to create xml out of dict

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
        return self._request('GET', "%s/daily" % self.uri)

    def get_day(self, day_of_the_year=1, year=2012):
        return self._request('GET', '%s/daily/%s/%s' % (self.uri, day_of_the_year, year))

    def get_entry(self, entry_id):
        return self._request("GET", "%s/daily/show/%s" % (self.uri, entry_id))

    def toggle_timer(self, entry_id):
        return self._request("GET", "%s/daily/timer/%s" % (self.uri, entry_id))

    def add(self, data):
        return self._request("POST", '%s/daily/add' % self.uri, data)

    def delete(self, entry_id):
        return self._request("DELETE", "%s/daily/delete/%s" % (self.uri, entry_id))

    def update(self, entry_id, data):
        return self._request('POST', '%s/daily/update/%s' % (self.uri, entry_id), data)

    def _request(self, type="GET", url="", data=None ):
        """
        type = request type, eg. GET, POST, DELETE
        url = full url to make request to, eg. https://MYCOMPANY.harvestapp.com/daily
        data = data for the request, leave empty for get requests

        """
        if type != "DELETE":
            if data:
                self.headers["Accept"] = 'application/xml'
                data = self._build_xml(data)
                request = urllib2.Request(url=url, data=data, headers=self.headers)
                self.headers["Accept"] = 'application/json'
            else:
                if not url.endswith(".json"): #dont put headers it a status request
                    request = urllib2.Request(url=url, headers=self.headers)
                else:
                    request = urllib2.Request(url=url)

            try:
                r = urllib2.urlopen(request)
                if not data:
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
                return opener.open(request).read()
            except Exception as e:
                raise HarvestError(e)

    def _build_xml(self, data_dict):
        def _builder(root, data):
            if type(data) == dict:
                for d in data.keys():
                    tag = doc.createElement(d)
                    root.appendChild(tag)
                    _builder(tag, data[d])
            else:
                root.appendChild(doc.createTextNode(str(data)))

        doc = Document()
        root = doc.createElement("request")
        doc.appendChild(root)
        _builder(root, data_dict)
        xml = doc.toprettyxml()
        return xml
