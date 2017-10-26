#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  websocket_server.py
#
#  Copyright 2016 Matteo D'Agord <matteo.dagord@gmail.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#

'''
This script runs a websocket server in order to exchange datas between remote
players and Strimy server.
It's based upon autobahn and twisted
'''

import os
import sys

# imports and initializes Django framework
import django

current_directory = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_directory + "/../")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "strimy.settings")
django.setup()

# imports Models and settings from Django
from devices.models import Dispositivi
# from playlist.models import PlaylistGenericaIndice
from users.models import UserGroups
# from stats.models import Statistiche
from django.utils import timezone
from django.conf import settings
from django import db

# imports libraries
from urlparse import urlparse
# import tornado.web
import socket
import json
import time
import datetime

# imports websocket libraries
from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory
from twisted.python import log
from twisted.internet import reactor, task
try:
    from twisted.internet import ssl
except:
    pass
from autobahn.twisted.websocket import WebSocketServerFactory

# imports external modules to manage interaction between browser (user), server,
# normal clients and conference clients
import websocket_functions_browser
import websocket_functions_device
import websocket_functions_device_conference
import websocket_functions_server

log_enabled = True
timeout_connection = 1800
ping_interval = settings.PING_INTERVAL

'''
message_content['type'] indica il tipo di messaggio scambiato tra browser/server
e client, e puo' essere uno di questi:
command: usato per inviare comandi rapidi al client (es.: reboot, send report)
message: usato per inivare una richiesta generica al client (es.: comunica lo status)
json:    usato per inviare comandi complessi; deve essere usato in abbinato a
         message_content['json'] che contiene il messaggio vero e proprio (es.
         la nuova configurazione, playlist ecc.)
confirm: usato dal client per comunicare al server l'avvenuta ricezione del
         messaggio
'''


connected_devices = {}


class WSHandler(WebSocketServerProtocol):

    connections = []

    users_connessi_playlist = {}    # stores the number of users associated to a player/playlist
    current_index_playlist = {}     # stores the current index for every player/playlist

    def authenticate_connection(self, id):

        # Connection strings examples:
        # browser associated to a digital signage usage
        #  ws://localhost/strimy/user_1_uyrweirysdaihf
        # browser associated to a conference box usage
        #  ws://localhost/strimy/user&80&12131231&xdxckdfdfjdfdxiouio98as&10

        parametro = id.split("&")

        if len(parametro) > 1:
            tipologia = "browser_conference"

        elif parametro[0][0:4] == "user":
            tipologia = "browser"

        else:
            tipologia = "device"

        if tipologia == "browser":

            gruppo = UserGroups.objects.filter(ugrp_stringa=parametro[0])
            if len(gruppo) > 0:
                gruppo = gruppo.get()
                if gruppo.ugrp_tipologia == 0:
                    self.amministratore = 1
                else:
                    self.amministratore = 0
                self.playlist_id = 0
                self.descrizione = ""
                self.device_id = 0
                self.tipologia = tipologia
                self.gruppo = gruppo.ugrp_id_group_id
                self.session_id = ""
                self.connection_time = time.time()
                self.connections.append(self)
                return True
            else:
                return False

        elif tipologia == "browser_conference":
            # parametro[0] = "user"
            # parametro[1] = playlist id
            # parametro[2] = device activation key
            # parametro[3] = browser session id
            try:
                dispositivi = Dispositivi.objects.get(
                    attivato=1, activation_key=parametro[2])
            except:
                return False

            try:
                playlist = PlaylistGenericaIndice.objects.get(pk=parametro[1])
                gruppo_id = playlist.ugrp_id_group_id
            except:
                gruppo_id = 0

            self.tipologia = tipologia
            self.descrizione = ""
            self.amministratore = 0
            self.gruppo = gruppo_id
            self.playlist_id = parametro[1]
            self.device_id = parametro[2]
            self.session_id = parametro[3]
            self.account = int(parametro[4])
            self.connection_time = time.time()
            self.connections.append(self)

            websocket_functions_device_conference.add_client(self)
            return True

        elif tipologia == "device":
            ammesso = True
            error_reason = ""

            # check if client is authorized
            # 1. client must be activated and not suspended
            dispositivi = Dispositivi.objects.filter(
                attivato=1, sospeso=0, activation_key=id)

            if not dispositivi.exists():
                error_reason = "non presente o non attivato"
                ammesso = False
            else:
                dispositivo = dispositivi.get()
                self.write_log(str(id)+": verifico le condizioni di accesso "
                            "(device "+ dispositivo.descrizione + ")...")

            # 2. there must be no client already connected using the same id
            for conn in self.connections:
                if conn.tipologia[0:6] == "device" and str(conn.id) == id:
                    error_reason = "gia' connesso"
                    ammesso = False

            # 3. client meets requirements: connection is authorized
            if ammesso:
                gruppo_id = dispositivo.ugrp_id_group_id
                self.device_pk = dispositivo.pk
                self.device_id = id
                self.gruppo = gruppo_id
                # client type can "digital_signage" (default) or "conference_box"
                if dispositivo.usage_type == "digital_signage":
                    connected_devices[self.device_id] = time.time()
                    self.tipologia = tipologia
                elif dispositivo.usage_type == "conference_box":
                    self.tipologia = "device_conference"
                    self.playlist_id = 0
                self.amministratore = 0
                self.descrizione = dispositivo.descrizione
                self.connection_time = time.time()
                self.connections.append(self)
                self.write_log(str(id) + ": regolarmente connesso al websocket :)")
                return True

            # the client is rejected: track down the event
            else:
                self.write_log(str(id) + ": non ammesso (%s) :(" % error_reason)
                self.sendClose()
                time.sleep(1)

        return False

    def onOpen(self):
        # opens connections

        # Connection strings examples:
        # ws://localhost/strimy/user_1_uyrweirysdaihf
        # ws://localhost/strimy/user&80&12131231&xdxckdfdfjdfdxiouio98as&10
        # ws://test.strimy.tv/strimy/12131231

        self.write_log(str(self.id)+": connessione in ingresso...")

        if self.authenticate_connection(self.id):

            self.check_db_timeout()

            if self.tipologia[0:6] == "device":

                message_content = {}
                message_content['message'] = "connected"
                message_content['type'] = "message"

                websocket_functions_browser.send_message(self, message_content)
                websocket_functions_device.get_messages(self)

        else:
            self.write_log(str(self.id)+": tentativo respinto!")
            self.sendClose()
            time.sleep(1)

    def onConnect(self, request):
        # accepts the connection
        id_temp = request.path.split('/')
        try:
            self.id = id_temp[2]
        except:
            self.id = id_temp[1]

    def request_messages(self):
        websocket_functions_device.get_messages(self)

    # sends a message
    def send_composed_message(self, conn, message):
        try:
            conn.sendMessage(json.dumps(message), isBinary=False)
            if message['message_content']['message'] == "remove_device":
                reactor.callLater(5, conn.sendClose)
        except:
            pass

    # gets a message
    def onMessage(self, content, isBinary):
        ammesso = True
        try:
            message = json.loads(content.decode('utf8'))
            message_content = message['message_content']
        except:
            message = {}
            ammesso = False

        # tries to parse the message and to send it according
        # to the recipient(s)
        if ammesso and 'message_sender' in message:

            if message['message_recipient']['type'][0:7] == "browser":
                websocket_functions_browser.send_message(self, message_content,
                                        message['message_recipient']['type'])

            elif message['message_recipient']['type'] == "device_conference":
                websocket_functions_device_conference.send_message(self,
                                            message_content)

            elif message['message_recipient']['type'][0:6] == "device":
                websocket_functions_device.send_message(self, message_content,
                                        message['message_recipient']['id'])

            elif message['message_recipient']['type'] == "server":
                websocket_functions_server.send_command(self, message_content)

            else:
                ammesso = False

        else:
            ammesso = False

        if not ammesso:
            print "message not allowed:"
            print message

    def onClose(self, wasClean, code, reason):
        try:
            self.write_log(str(self.id) + ": disconnesso 0 " +
                        self.tipologia + " (" + self.descrizione + ")")
        except:
            self.tipologia = ""

        if self.tipologia == "browser_conference":
            websocket_functions_device_conference.remove_client(self)

        if self.tipologia[0:6] == "device":
            try:
                message_content = {}
                message_content['message'] = "disconnected"
                message_content['type'] = "message"
                message_content['error_code'] = 0

                websocket_functions_browser.send_message(self, message_content)

            except:
                pass

        if self.tipologia == "device_conference":
            websocket_functions_device_conference.refresh_clients(self, 0)

        try:
            self.connections.remove(self)
        except:
            pass

    def check_db_timeout(self):
        # this function checks on a regular basis fi the db connection is
        # "older" than the specified timeout (in seconds);
        # if so, it forces the connection to close in order to prevent the
        # MySql server error n. 2006 (mysql server has gone away)
        differenza = int(time.time() - self.connection_time)
        if differenza > timeout_connection:
            try:
                db.connection.close()
                self.connection_time = time.time()
            except:
                pass

        reactor.callLater(timeout_connection, self.check_db_timeout)

    def onPong(self, data):
        if self.tipologia == "device":
            connected_devices[self.device_id] = time.time()

    def check_origin(self, origin):
        return True

    def write_log(self, message):
        if log_enabled:
            print time.strftime('%d/%m/%y - %H:%M:%S | ' + str(message))
            message_to_log = time.strftime('%d/%m/%y - %H:%M:%S | ') +
                             str(message) + '\n'
            try:
                file_log = open(current_directory + '/websocket.log', 'a')
                file_log.write(message_to_log)
                file_log.close()
            except:
                pass

    # this task checks on a regular basis if the remote client is still
    # responding
    def track_connections():
        orario_attuale = time.time()
        connected_devices_copy = connected_devices.copy()
        if len(connected_devices) > 0:
            for connessione in connected_devices_copy:
                differenza = orario_attuale-connected_devices[connessione]
                if differenza > (ping_interval*3):
                    update_time = time.strftime('%d/%m/%y - %H:%M:%S')
                    websocket_functions_server.send_disconnected_message(
                                connessione, update_time)
                    connected_devices.pop(connessione)

    # adds the track_connections task
    task.LoopingCall(track_connections).start(ping_interval)


if __name__ == "__main__":

    websocket_url = urlparse(settings.WEBSOCKET_URL)

    porta = websocket_url.port
    factory = WebSocketServerFactory()
    factory.protocol = WSHandler
    factory.setProtocolOptions(autoPingInterval=ping_interval,
        autoPingTimeout=int(ping_interval/2))
    if websocket_url.scheme.lower() == "wss":
        contextFactory = ssl.DefaultOpenSSLContextFactory(
            settings.SSL_PRIVATEKEY, settings.SSL_CERTFILE)
        reactor.listenSSL(porta, factory, contextFactory)
    else:
        reactor.listenTCP(porta, factory)

    reactor.run()
