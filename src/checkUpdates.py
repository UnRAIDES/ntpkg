#!/usr/bin/python3


import argparse
import os
import requests
import re
import wget
import shutil
import configparser
import json
import asyncio
import time
import schedule

from bs4 import BeautifulSoup
from pkg_resources import parse_version
from pathlib import Path
from packaging import version
from datetime import datetime, timedelta

from telegram import Bot


__version__ = "VERSION 0.0.3"

default_interval_hours = int(os.getenv("INTERVALO_HORAS", 24))
interval_seconds = default_interval_hours * 60 * 60
hours_env = os.getenv("SPECIFIC_HOURS", "").split(",")

class NTPKGS:

    def __init__(self):
        self.args = self.parse_args()
        self.config = self.config()
        self.url = self.args.url
        self.packages = []
        self.slackware64 = []


        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

        self.download_path = self.args.download_path if self.args.download_path else self.config.get('DOWNLOAD', 'downloadpath')
        #self.packages = self.args.packages      if self.args.packages else self.config.get('PACKAGES', 'packagespath')

        #os.makedirs(self.download_path, exist_ok=True)

        self.getListPackages()
        self.getStableList()
        #self.checkUpdates()
        asyncio.run(self.checkUpdates())
        asyncio.run(self.slackbuilds())


    def parse_args(self):
        parser = argparse.ArgumentParser(description="ntpkgs update")

        parser.add_argument('-v','--version', action='version', version="%(prog)s " + __version__)
        
        parser.add_argument('-d', '--download', action='store_true', help='download files')
        parser.add_argument('-u', '--update', action='store_true', help='update files')
    
        parser.add_argument('--download-path', help='download path')
        parser.add_argument('--packages', help='origin package path')

        parser.add_argument('--url', help='url source example: https://mirrors.slackware.com/slackware/slackware64-current/CHECKSUMS.md5', default="https://mirrors.slackware.com/slackware/slackware64-current/CHECKSUMS.md5")
                
        return parser.parse_args()

    def getListPackages(self):
        print(f" [!] getListPackages \n", flush=True)
        url = "https://api.github.com/repos/UnRAIDES/unRAID-NerdTools/contents/packages/pkgs"


        response = requests.get(url)

        # Verificar si la solicitud fue exitosa (código de estado 200)
        if response.status_code == 200:
            # Convertir la respuesta JSON a un diccionario de Python
            data = json.loads(response.text)

            # Iterar sobre los elementos en el directorio e imprimir los nombres
            for item in data:
                if "name" in item:
                    self.packages.append(item["name"])
                    #print(item["name"])
        else:
            # Imprimir un mensaje de error si la solicitud no fue exitosa
            print(f"Error al hacer la solicitud. Código de estado: {response.status_code}", flush=True)

    def getStableList(self):
        url = "https://mirrors.slackware.com/slackware/slackware64-15.0/CHECKSUMS.md5"

        #if os.path.exists("slackware64.txt"):
        #    print(f"getStableList path.exists slackware64.txt:: ", flush=True)
        #
        #    with open("slackware64.txt", 'r') as archivo:
        #        for line in archivo:
        #            #print(f"slackware:: {line}")
        #            if "txz" in line and ".asc" not in line:
        #                split = line.split("./")[1]
        #                self.slackware64.append(split)
        #                #print(f"slackware:: {split}")
        #
        #else:

        base_url = os.path.dirname(url)
        payload={}
        headers = {}

        response = requests.request("GET", url, headers=headers, data=payload)

        source = response.text
        soup = BeautifulSoup(response.text, "html.parser") # lxml is just the parser for reading the html
        links = soup.find_all('a')
        #print(response.text)
        respon = response.text

        with open("slackware64.txt", 'w') as archivo:
            archivo.write(response.text)

        for line in response.iter_lines(decode_unicode=True):
            if "txz" in line and ".asc" not in line:
                split = line.split("./")[1]
                self.slackware64.append(split)
                #print(f"slackware:: {split}")
 
    async def checkUpdates(self):

        
        try:

            for package in self.packages:

                print(f" [**] slackware64:: package: {package}", flush=True)

                #pattern  = '/^([a-zA-Z0-9-]+)-([\d.]+)-?.*\.txz$/'

                _package = re.match(r'^(.+?)-\d.*', package)[1]
                _version = re.match(r'^(.+?)-([\d.]+)-?.+?\.txz', package)[2]


                #print(f"package:: {package}")
                #print(f"_package:: {_package}")
                #print(f"_version:: {_version}")

                for slackware64 in self.slackware64:
                    #print(f"slackware64:: {slackware64}")
                    if re.match(fr'.*\W{_package}-\d.*', slackware64):
                        print(f" [**] slackware64:: _package: {_package}", flush=True)

                        _Spackage = re.match(r'^.*\/(.+?)-\d.*', slackware64)[1]
                        _Sversion = re.match(r'^.*\/(.+?)-([\d.]+)-?.+?\.txz', slackware64)[2]
                        #print(f"slackware64:: {_Spackage}")
                        #print(f"slackware64:: {_Sversion}")
                        #print(f"slackware64:: {slackware64}")

                        if _version != _Sversion:
                            print(f" [**] slackware64:: package: {_package} version: {_version} <==> Package: {_Spackage} Version: {_Sversion}  ==> {package}", flush=True)

                            update = parse_version(re.sub(r'[a-zA-Z]', '', _version)) < parse_version(re.sub(r'[a-zA-Z]', '', _Sversion))
                            if update:
                                await self.send_telegram_message(f"package: {_package} version: {_version} new version: {_Sversion}")
                                print(f"         UPDATE  [*] [{update}] [{_package}]", flush=True)


                #print(f"")

        except Exception as e:
            print(f"checkUpdates Exception [{e}]", flush=True)
            await self.send_telegram_message(f"checkUpdates Exception: {e}")



    async def slackbuilds(self):
        try:
            
            source_packages = []

            url = "https://slackbuilds.org/slackbuilds/15.0/SLACKBUILDS.TXT"
            response = self.getResponse(url)
            print(f"\n [!] slackbuilds.org \n", flush=True)

            if not self.packages: return

            for line in response.iter_lines(decode_unicode=True):
                if "NAME:" in line:
                    NAME = line
                    NAME = line.split(":")[1].strip()
                    _NAME = re.escape(NAME)
                if "LOCATION:" in line:
                    LOCATION = line
                    LOCATION = line.split(":")[1].strip().replace("./", "/")
                    source_packages.append(NAME)
                    base_url = os.path.dirname(url)
                    new_url = f"{base_url}{LOCATION}"
                if "VERSION:" in line:
                    VERSION = line
                    VERSION = line.split(":")[1].strip()


                    for package in self.packages:

                        #print(f" [**] slackbuilds:: package: {package}", flush=True)

                        _package = re.match(r'^(.+?)-\d.*', package)[1]
                        #_version = re.match(r'^[a-zA-Z]?(\d+(\.\d+)*)', _version)[1]
                        _version = re.match(r'^(.+?)-([\d.]+)-?.+?\.txz', package)[2]

                        _VERSION = re.match(r'^[a-zA-Z]?(\d+(\.\d+)*)', VERSION)

                        if not _VERSION: continue

                        _VERSION = _VERSION.group(1)

                        if re.match(f'^{_NAME}$', _package):
                            print(f" [**] slackware64:: package: {_package} version: {_version} <==> Package: {_NAME} Version: {_VERSION}  ==> {package}", flush=True)
                            update = parse_version(_version) < parse_version(_VERSION) if not "_" in _VERSION else True
                            if update:
                                print(f" UPDATE  [*] [{update}] [{_package}]  \t-->   [{_package}] [{_version}] >> [{NAME}] [{_VERSION}]  [{new_url}]", flush=True)
                                await self.send_telegram_message(f"package: {_package} version: {_version} new version: {VERSION}\n{new_url}")


        except Exception as e:
            print(f" [!] slackbuilds Exception [{e}]", flush=True)
            await self.send_telegram_message(f"slackbuilds Exception: {e}")

    async def send_telegram_message(self, mensaje):
        try:
            print(f" [!] send_telegram_message [{mensaje}]", flush=True)
            bot = Bot(token=self.token)
            await bot.send_message(chat_id=self.chat_id, text=mensaje)
        except Exception as e:
            print(f" [!] send_telegram_message Exception [{e}]", flush=True)








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
            print(f" [!] updatePackage [{e}]", flush=True)
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
        print(f" [!] config [{config.DOWNLOAD}]", flush=True)



def main():
    nt = NTPKGS()
    #nt.CHECKSUMS()
    #nt.SLACKBUILDS()
    
    current_time = datetime.now()
    print(f"Current date and time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)


if __name__ == "__main__":
    scheduled_hours = []

    # Schedule the function to run at the specific hours
    for hour in hours_env:
        scheduled_hours.append(hour)
        schedule.every().day.at(hour).do(main)


    current_time = datetime.now()
    print(f"Current date and time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("Scheduled hours:", scheduled_hours, flush=True)
    
    while True:

        schedule.run_pending()

        time.sleep(60)


