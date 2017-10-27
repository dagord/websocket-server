#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  websocket_functions_server.py
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
This module extends base websocket module and enables communication with
remote "digital signage" Strimy players
'''
from devices.models import DispositiviComandiWebsocket
from devices.devices_views import comandi_websocket_save
import json


def send_message(connessione, message_content_to_send, recipient_id=""):

        message = {}

        message_sender = {}
        message_sender['id'] = connessione.device_id
        message_sender['type'] = connessione.tipologia

        message_recipient = {}
        message_recipient['id'] = recipient_id
        message_recipient['type'] = "device"

        message['message_content'] = message_content_to_send
        message['message_sender'] = message_sender
        message['message_recipient'] = message_recipient

        device_connesso = 0

        for conn in connessione.connections:

            if ((conn.gruppo == connessione.gruppo or connessione.amministratore == 1)
            and conn.tipologia[0:6] == "device"
            and str(conn.device_id) == str(message['message_recipient']['id'])):
                connessione.send_composed_message(conn, message)
                device_connesso = 1

        if device_connesso == 0 and message_content_to_send['type'] == "json":
            comandi_websocket_save(
                message_recipient['id'], message_sender['id'],
                message_content_to_send['message'],
                message_content_to_send['json']
                )


# if the server sent some messages while the player was disconnected, the
# queue is stored in the database
# use this function to retrive them (if any)
def get_messages(connessione):
    dispositivi_comandi_websocket = DispositiviComandiWebsocket.objects.filter(
        activation_key=connessione.device_id).order_by('orario')

    for dispositivi_comandi_websocket_temp in dispositivi_comandi_websocket:

        message_content = {}
        message_content['type'] = "json"
        message_content['message'] = dispositivi_comandi_websocket_temp.comando
        message_content['json'] = json.loads(dispositivi_comandi_websocket_temp.contenuto)
        dispositivi_comandi_websocket_temp.delete()

        message_recipient = {}
        message_recipient['id'] = connessione.device_id
        message_recipient['type'] = "device"

        message_sender = {}
        message_sender['id'] = dispositivi_comandi_websocket_temp.sender
        message_sender['type'] = "browser"

        message = {}
        message['message_content'] = message_content
        message['message_sender'] = message_sender
        message['message_recipient'] = message_recipient

        connessione.send_composed_message(connessione, message)
