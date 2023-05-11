#!/usr/bin/python3


import argparse
import os
import requests
import re
import wget
import shutil
import configparser

from bs4 import BeautifulSoup
from pkg_resources import parse_version
from pathlib import Path


__version__ = "VERSION 0.0.4"



class NTPKGS:

    def __init__(self):
        self.args = self.parse_args()
        self.config = self.config()
        self.url = self.args.url
        self.args.download = True if self.args.update else self.args.download
        self.download_path = self.args.download_path if self.args.download_path else self.config.get('DOWNLOAD', 'downloadpath')
        self.packages = self.args.packages if self.args.packages else self.config.get('PACKAGES', 'packagespath')

        os.makedirs(self.download_path, exist_ok=True)

    def parse_args(self):
        parser = argparse.ArgumentParser(description="ntpkgs update")

        parser.add_argument('-v','--version', action='version', version="%(prog)s " + __version__)
        
        parser.add_argument('-d', '--download', action='store_true', help='download files')
        parser.add_argument('-u', '--update', action='store_true', help='update files')
    
        parser.add_argument('--download-path', help='download path')
        parser.add_argument('--packages', help='origin package path')

        parser.add_argument('--url', help='url source example: https://mirrors.slackware.com/slackware/slackware64-current/CHECKSUMS.md5', default="https://mirrors.slackware.com/slackware/slackware64-current/CHECKSUMS.md5")
                
        return parser.parse_args()

    def CHECKSUMS(self):

        print(f" [!] mirrors.slackware.com \n")

        url = "https://slackware.uk/slackware/slackware64-15.0/slackware64/CHECKSUMS.md5"
        url = "https://mirrors.slackware.com/slackware/slackware64-current/CHECKSUMS.md5"
        url = self.url

        base_url = os.path.dirname(url)
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
        if not os.path.exists(self.packages):return

        for path in os.listdir(self.packages):
            if os.path.isfile(os.path.join(self.packages, path)):
                try:
                    package = re.match('^(.+?)-\d.*', path)[1]
                    version = re.match('^(.+?)-(\d.+?)(:?-|_).*', path)[2]
                    #update = parse_version('2.1-rc2') < parse_version('2.1')
                    for pack in source_packages:
                        if re.match(f'.*\W{package}-\d.*', pack):
                            version2 = re.match('^(.+?)-(\d.+?)(:?-|_).*', pack)[2]
                            update = parse_version(version) < parse_version(version2)
                            if update:
                                print(f" UPDATE  [*] [{update}] [{package}] -->   [{path}] [{version}]  >>> [{pack}] [{version2}][{update}]")
                                if self.args.download:
                                    new_url = f"{base_url}/{pack}"
                                    filename = self.updatePackage(new_url)
                                    if self.args.update:
                                        os.makedirs(os.path.join("/","tmp"), exist_ok=True)
                                        shutil.move(os.path.join(self.packages,path), os.path.join("/","tmp",path))
                                        shutil.move(filename, self.packages)
                            #else:
                            #    print(f" [*] [{update}] [{package}] -->   [{path}] [{version}]  >>> [{pack}] [{version2}]")
                except Exception as e:
                    print(f" [!] CHECKSUMS Exception [{e}]")
    

    def SLACKBUILDS(self):
        try:
            
            source_packages = []

            url = "https://slackbuilds.org/slackbuilds/15.0/SLACKBUILDS.TXT"
            response = self.getResponse(url)
            print(f"\n [!] slackbuilds.org \n")


            packages = self.listdir()
            if not packages: return

            for line in response.iter_lines(decode_unicode=True):
                if "NAME:" in line:
                    NAME = line
                    NAME = line.split(":")[1].strip()
                if "LOCATION:" in line:
                    LOCATION = line
                    LOCATION = line.split(":")[1].strip().replace("./", "/")
                    source_packages.append(NAME)
                    base_url = os.path.dirname(url)
                    new_url = f"{base_url}{LOCATION}"
                if "VERSION:" in line:
                    VERSION = line
                    VERSION = line.split(":")[1].strip()

                    for path in packages:
                        _package_origin = re.match('^(.+?)-\d.*', path)[1]
                        _version_origin = re.match('^(.+?)-(\d.+?)(:?-|_).*', path)[2]
                        
                        _NAME = re.escape(NAME)

                        if re.match(f'^{_NAME}$', _package_origin):
                            update = parse_version(_version_origin) < parse_version(VERSION) if not "_" in VERSION else True
                            if update:
                                print(f" UPDATE  [*] [{update}] [{_package_origin}] -->   [{_package_origin}] [{_version_origin}] >> [{NAME}] [{VERSION}]  [{new_url}]")


        except Exception as e:
            print(f" [!] SLACKBUILDS Exception [{e}]")
    

    def listdir(self):

        if not os.path.exists(self.packages): return False

        packages = []
        for path in os.listdir(self.packages):
            packages.append(path)
        return packages

    def getResponse(self, url):

        base_url = os.path.dirname(url)
        payload={}
        headers = {}

        response = requests.request("GET", url, headers=headers, data=payload)

        source = response.text
        soup = BeautifulSoup(response.text, "html.parser") # lxml is just the parser for reading the html
        links = soup.find_all('a')
        #print(response.text)

        return response

    def updatePackage(self, url):
        try:
            os.makedirs(self.download_path, exist_ok=True)
            #url = f"https://mirrors.slackware.com/slackware/slackware64-current/{package}"
            filename = wget.download(url, out=self.download_path, bar=None)
            return filename
        except Exception as e:
            print(f" [!] updatePackage [{e}]")
            return False

    def config(self):
        ruta_config = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config.ini'))

        config = configparser.ConfigParser()
        config.read(ruta_config)

        # Si la sección 'NUEVA_SECCION' no existe, se agrega al archivo
        if 'DOWNLOAD' not in config:
            config.add_section('DOWNLOAD')
        if 'PACKAGES' not in config:
            config.add_section('PACKAGES')
            
        # Agregar un nuevo valor a la sección 'DOWNLOAD' si no existe
        if 'downloadpath' not in config['DOWNLOAD']:
            config.set('DOWNLOAD', 'downloadpath', 'download')
        # Agregar un nuevo valor a la sección 'PACKAGES' si no existe
        if 'packagespath' not in config['PACKAGES']:
            config.set('PACKAGES', 'packagespath', 'unRAID-NerdTools/packages/pkgs')

        # Escribir los cambios en el archivo
        with open(ruta_config, 'w') as f:
            config.write(f)

        return config
        print(f" [!] config [{config.DOWNLOAD}]")



def main():
    nt = NTPKGS()
    nt.CHECKSUMS()
    nt.SLACKBUILDS()


if __name__ == "__main__":
    main()
