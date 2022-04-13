from http.server import BaseHTTPRequestHandler, HTTPServer
from lxml import etree
from decimal import Decimal

import urllib.request
import json
import sys

ULP = 1
PULP = 2 # Premium ULP (95)
NORTH_OF_RIVER = 25
SOUTH_OF_RIVER = 26

TODAY = False
TOMORROW = True

def items_generator(tomorrow, items):
    for item in items:
        title = item.find('./title').text
        price, extra = title.split(':', 1)

        description = item.find('./description').text
        location = item.find('./location').text
        brand = item.find('./brand').text

        yield Decimal(price), {
            'title': title,
            'price': price,
            'description': description,
            'location': location,
            'tomorrow': tomorrow,
            'brand': brand,
        }

def locations_generator(fuel_type, tomorrow, locations, date_row=False):
    for i, location in enumerate(locations):
        url = 'http://www.fuelwatch.wa.gov.au/fuelwatch/fuelWatchRSS?Product={0}&Region={1}{2}'.format(fuel_type, location, '&Day=tomorrow' if tomorrow else '')

        req = urllib.request.Request(url, headers={ 'User-Agent' : '' })
        rss = urllib.request.urlopen(req).read()

        root = etree.fromstring(rss)
        if i == 0 and date_row:
            date = root.find('./channel/lastBuildDate').text
            first_few_characters = date[0:10]
            cleaned_date = date[0:date.rindex(first_few_characters)]

            yield 0, {
                'price': '',
                'title': '',
                'description': cleaned_date,
                'location': '',
                'tomorrow': False,
                'brand': '',
            }

        for item in items_generator(tomorrow, root.findall('.//item')):
            yield item

def generate(fuel_type):
    for item in locations_generator(fuel_type, TODAY, (SOUTH_OF_RIVER, NORTH_OF_RIVER), date_row=True):
        yield item

    for item in locations_generator(fuel_type, TOMORROW, (SOUTH_OF_RIVER, NORTH_OF_RIVER)):
        yield item

def table(content):
    return '<table>' + content + '</table>'

def tr(content, alt=False):
    attr = ' style="background:#ffdddd"' if alt else ''
    return f'<tr{alt}>{content}</tr>'

def td(content):
    return f'<td>{content}</td>'

def fuel_table(fuel_type):
    return table(''.join(
        tr(
            ''.join(td(d[k]) for k in ('price', 'location', 'description', 'brand')),
            bool(d['tomorrow']))
        for price, d in sorted(generate(fuel_type), key=lambda t: t[0])))

def send_headers(server):
    server.send_header('Content-Type', 'text/html')
    server.end_headers()

class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        send_headers(self)
        self.wfile.write(fuel_table(PULP).encode())

if __name__ == '__main__':
    host, port = sys.argv[1:3]
    print("Server started http://%s:%s" % (host, port))
    web_server = HTTPServer((host, int(port)), MyServer)

    try:
        web_server.serve_forever()
    except KeyboardInterrupt:
        pass

    web_server.server_close()
    print("Server stopped.")
