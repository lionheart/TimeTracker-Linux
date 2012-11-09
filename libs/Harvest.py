'''
>>> import Harvest
>>> Harvest.HarvestStatus().get()
u'up'
>>> harvest = Harvest.Harvest("https://COMPANYNAME.harvestapp.com", "EMAIL", "PASSWORD")
>>> data = {"notes":"test note", "project_id":"PROJECT_ID","hours":"1.0", "task_id": "TASK_ID"}
>>> harvest.add(data)
>>> data['notes'] = "another test"
>>> harvest.update("ENTRY_ID", data)
>>> harvest.get_today()

'''

from xml.dom.minidom import Document #to create xml out of dict

import requests
from requests.auth import HTTPBasicAuth

class HarvestError(Exception):
    pass

class Harvest(object):
    def __init__(self, uri, email, password):
        self.uri = uri
        self.email = email
        self.password = password
        self.headers = {
            'Accept': 'application/json',
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
    def _request(self, type = "GET", url = "", data = None):
        if type != "DELETE":
            if data:
                r = requests.post(url, data=data, headers=self.headers, auth=HTTPBasicAuth(self.email, self.password))
            else:
                if not url.endswith(".json"): #dont put headers it a status request
                    r = requests.get(url=url, headers=self.headers, auth=HTTPBasicAuth(self.email, self.password))
                else:
                    r = requests.get(url)

            try:
                return r.json
            except Exception as e:
                raise HarvestError(e)

        else:
            try:
                r = requests.delete(url, headers=self.headers, auth=HTTPBasicAuth(self.email, self.password))
            except Exception as e:
                raise HarvestError(e)

class HarvestStatus(Harvest):
    def __init__(self):
        self.harvest = Harvest("", "", "").status()

    def get(self):
        return self.harvest['status']
