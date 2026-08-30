
import csv
import http.client
import io
import urllib

class OurAirports():

    host = "davidmegginson.github.io"

    @classmethod
    def _get_data(cls, path):
        url = urllib.parse.urlunparse(("", "", path, "", "", ""))

        connect = http.client.HTTPSConnection(OurAirports.host)
        connect.request("GET", url)
        response = connect.getresponse()

        if response.status == 200:

            data = io.TextIOWrapper(response, encoding="utf-8")
            return csv.DictReader(data)
        else:
            return None

    @classmethod
    def countries(cls):
        return OurAirports._get_data("/ourairports-data/countries.csv")

    @classmethod
    def regions(cls):
        return OurAirports._get_data("/ourairports-data/regions.csv")

    @classmethod
    def airports(cls):
        return OurAirports._get_data("/ourairports-data/airports.csv")

    @classmethod
    def runways(cls):
        return OurAirports._get_data("/ourairports-data/runways.csv")

    @classmethod
    def frequencies(cls):
        return OurAirports._get_data("/ourairports-data/airport-frequencies.csv")
