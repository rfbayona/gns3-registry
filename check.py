#!/usr/bin/env python
#
# Copyright (C) 2015 GNS3 Technologies Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import jsonschema
import json
import sys
import subprocess
import urllib.request
from multiprocessing import Pool


class MyHTTPRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        return None

urllib.request.install_opener(urllib.request.build_opener(MyHTTPRedirectHandler))

def check_url(url, appliance):
    try:
        print("Check " + url)
        req = urllib.request.Request(url, method='HEAD')
        urllib.request.urlopen(req, 5)
    except urllib.error.HTTPError as err:
        if err.getcode() >= 400:
            print('Error with url ' + url + ' - ' + str(err))
            sys.exit(1)
    except urllib.error.URLError:
        print('Invalid URL ' + url)
        sys.exit(1)


def check_appliance(appliance):
    global images
    images = set()
    global md5sums
    md5sums = set()

    with open('schemas/appliance.json') as f:
        schema = json.load(f)

    with open(os.path.join('appliances', appliance)) as f:
        appliance_json = json.load(f)
        jsonschema.validate(appliance_json, schema)

    for image in appliance_json['images']:
        if image['filename'] in images:
            print('Duplicate image filename ' + image['filename'])
            sys.exit(1)
        if image['md5sum'] in md5sums:
            print('Duplicate image md5sum ' + image['md5sum'])
            sys.exit(1)
        images.add(image['filename'])
        md5sums.add(image['md5sum'])

    for version in appliance_json['versions']:
        for image in version['images'].values():
            found = False
            for i in appliance_json['images']:
                if i['filename'] in image:
                    found = True

            if not found:
                print('Missing relation ' + i['filename'] + ' ' + ' in ' + appliance)
                sys.exit(1)


def check_urls(pool, appliance):
    with open(os.path.join('appliances', appliance)) as f:
        appliance_json = json.load(f)

    for image in appliance_json['images']:
        if 'direct_download_url' in image:
            pool.apply_async(check_url, [image['direct_download_url'], appliance])
        if 'download_url' in image:
            pool.apply_async(check_url, [image['download_url'], appliance])

    if 'vendor_url' in appliance_json:
        pool.apply_async(check_url, [appliance_json['vendor_url'], appliance])
    if 'documentation_url' in appliance_json:
        pool.apply_async(check_url, [appliance_json['documentation_url'], appliance])
    if 'product_url' in appliance_json:
        pool.apply_async(check_url, [appliance_json['product_url'], appliance])


def check_packer(packer):
    path = os.path.join('packer', packer)
    if not os.path.isdir(path):
        return
    for file in os.listdir(path):
        if file.endswith('.json'):
            print('Check {}/{}'.format(packer, file))
            with open(os.path.join('packer', packer, file)) as f:
                json.load(f)


def check_symbol(symbol):
    licence_file = os.path.join('symbols', symbol.replace('.svg', '.txt'))
    if not os.path.exists(licence_file):
        print("Missing licence {} for {}".format(licence_file, symbol))
        sys.exit(1)
    height = int(subprocess.check_output(['identify', '-format', '%h', os.path.join('symbols', symbol)], shell=False))
    if height > 70:
        print("Symbol height of {} is too big {} > 70".format(symbol, height))
        sys.exit(1)


def main():
    pool = Pool(processes=8)

    print("=> Check appliances")
    for appliance in os.listdir('appliances'):
        print('Check {}'.format(appliance))
        check_appliance(appliance)
        check_urls(pool, appliance)
    print("=> Check symbols")
    for symbol in os.listdir('symbols'):
        if symbol.endswith('.svg'):
            print('Check {}'.format(symbol))
            check_symbol(symbol)
    print("=> Check packer files")
    for packer in os.listdir('packer'):
        check_packer(packer)
    print("=> Check URL in appliances")
    pool.close()
    pool.join()

if __name__ == '__main__':
    main()
