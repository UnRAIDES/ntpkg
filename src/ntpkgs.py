#!/usr/bin/python3


import argparse
import os
import requests
import re
import wget
import shutil
from bs4 import BeautifulSoup
from pkg_resources import parse_version
from pathlib import Path


__version__ = "VERSION 0.0.2"



class NTPKGS:

    def __init__(self):
        self.args = self.parse_args()
        self.download_path = self.args.download_path
        self.packages = self.args.packages
        self.url = self.args.url

    def parse_args(self):
        parser = argparse.ArgumentParser(description="MKV Tools - Delete Spam.")

        parser.add_argument('-v','--version', action='version', version="%(prog)s " + __version__)
        
        parser.add_argument('-d', '--download', action='store_true', help='download files')
        parser.add_argument('-u', '--update', action='store_true', help='update files')
    
        parser.add_argument('--download-path', help='download path', default="/download")
        parser.add_argument('--packages', help='download path', default="/packages")
        parser.add_argument('--url', help='url source example: https://mirrors.slackware.com/slackware/slackware64-current/CHECKSUMS.md5', default="https://mirrors.slackware.com/slackware/slackware64-current/CHECKSUMS.md5")
                
        return parser.parse_args()

    def main(self):

        url = "https://mirrors.slackware.com/slackware/slackware64/source/ap/"
        url = "https://slackware.uk/slackware/slackware64-15.0/slackware64/ap/"
        url = "https://mirrors.slackware.com/slackware/slackware64-current/CHECKSUMS.md5"
        url = self.url

        payload={}
        headers = {}

        response = requests.request("GET", url, headers=headers, data=payload)

        source = response.text
        soup = BeautifulSoup(response.text, "html.parser") # lxml is just the parser for reading the html
        links = soup.find_all('a')
        #print(response.text)
        source_packages = []

        for line in response.iter_lines(decode_unicode=True):
            if "txz" in line and ".asc" not in line:
                split = line.split("./")[1]
                source_packages.append(split)
        res = []

        for path in os.listdir(self.packages):
            if os.path.isfile(os.path.join(self.packages, path)):
                try:
                    package = re.match('^(.+?)-\d.*', path)[1]
                    version = re.match('^(.+?)-(\d.+?)(:?-|_).*', path)[2]
                    
                    update = parse_version('2.1-rc2') < parse_version('2.1')

                    for pack in source_packages:
                        if re.match(f'.*\W{package}-\d.*', pack):
                            version2 = re.match('^(.+?)-(\d.+?)(:?-|_).*', pack)[2]
                            update = parse_version(version) < parse_version(version2)
                            if update:
                                print(f" UPDATE  [*] [{update}] [{package}] -->   [{path}] [{version}]  >>> [{pack}] [{version2}][{update}]")
                                if self.args.download:
                                    filename = self.updatePackage(pack)
                                    if self.args.update:
                                        os.makedirs(os.path.join("/","backup"), exist_ok=True)
                                        shutil.move(os.path.join(self.packages,path), os.path.join("/","backup",path))
                                        shutil.move(filename, self.packages)
                            #else:
                            #    print(f" [*] [{update}] [{package}] -->   [{path}] [{version}]  >>> [{pack}] [{version2}]")
                except Exception as e:
                    print(f"   [!] Exception [{e}]")
    
    def updatePackage(self, package):
        try:
            os.makedirs(self.download_path, exist_ok=True)
            url = f"https://mirrors.slackware.com/slackware/slackware64-current/{package}"
            filename = wget.download(url, out=self.download_path, bar=None)
            return filename
        except Exception as e:
            print(f" [!] updatePackage [{e}]")
            return False


def main():
    nt = NTPKGS()
    nt.main()


if __name__ == "__main__":
    main()