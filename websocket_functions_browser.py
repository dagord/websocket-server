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
browsers/users
'''

import websocket_functions_device_conference
from conference.models import (
    ConferenceCommenti, ConferenceRisposte, ConferenceGiaRisposte)


def send_message(connessione, message_content_to_send, recipient="browser"):

    if recipient == "browser":

        message = {}

        message_sender = {}
        message_sender['id'] = connessione.id
        message_sender['type'] = connessione.tipologia

        message_recipient = {}
        message_recipient['id'] = connessione.gruppo
        message_recipient['type'] = "browser"

        message['message_content'] = message_content_to_send
        message['message_sender'] = message_sender
        message['message_recipient'] = message_recipient

        for conn in connessione.connections:
            if ((conn.gruppo == connessione.gruppo or conn.amministratore == 1)
                and conn.tipologia == "browser"):
                connessione.send_composed_message(conn, message)

    elif recipient == "browser_conference":

        try:
            playlist_id_temp = message_content_to_send['json']['playlist_id']
            if connessione.playlist_id != playlist_id_temp:
                connessione.playlist_id = playlist_id_temp
                ConferenceRisposte.objects.filter(
                    id_playlist_id=connessione.playlist_id,
                    activation_key=connessione.device_id).delete()
                ConferenceGiaRisposte.objects.filter(
                    id_playlist_id=connessione.playlist_id,
                    activation_key=connessione.device_id).delete()
                ConferenceCommenti.objects.filter(
                    id_playlist_id=connessione.playlist_id,
                    activation_key=connessione.device_id).delete()

        except:
            pass

        if 'message' not in message_content_to_send:
            message_content_to_send['message'] = ""

        # gets question results, and returns them both to players and to browsers
        if message_content_to_send['message'] == "request_answer_results":
            domande_gia_risposte = ConferenceGiaRisposte.objects.filter(
                id_playlist_id=int(connessione.playlist_id),
                activation_key=connessione.device_id,
                indice=message_content_to_send['json']['index'])
            if len(domande_gia_risposte) == 0:
                domande_gia_risposte = ConferenceGiaRisposte()
                domande_gia_risposte.id_playlist_id = int(connessione.playlist_id)
                domande_gia_risposte.activation_key = connessione.device_id
                domande_gia_risposte.indice = message_content_to_send['json']['index']
                domande_gia_risposte.save()

            array_risposte = websocket_functions_device_conference.recover_answers(
                connessione, message_content_to_send['json']['index'])

            content_to_send = {}
            content_to_send['index'] = message_content_to_send['json']['index']
            content_to_send['results'] = array_risposte

            message_content = compose_message("display_answer_results",
                                              content_to_send)
            # send results to player (conference box)
            websocket_functions_device_conference.send_message(connessione, message_content)
            # send results to browsers (users)
            send_message(connessione, message_content, "browser_conference")

        elif message_content_to_send['message'] == "delete_comments":
            commenti = ConferenceCommenti.objects.filter(
                id_playlist_id=connessione.playlist_id,
                activation_key=connessione.device_id)
            commenti.delete()
            content_to_send = {}
            message_content = compose_message("comments_deleted",
                                              content_to_send)
            send_message(connessione, message_content, "browser_conference")

        else:
            message = {}

            message_sender = {}
            message_sender['id'] = connessione.id
            message_sender['type'] = connessione.tipologia

            message_recipient = {}
            message_recipient['id'] = connessione.gruppo
            message_recipient['type'] = "browser_conference"

            message['message_content'] = message_content_to_send
            message['message_sender'] = message_sender
            message['message_recipient'] = message_recipient

            if message_content_to_send['message'] == "set_index":
                connessione.current_index_playlist[connessione.playlist_id,
                    connessione.device_id] = message_content_to_send['json']['index']

            for conn in connessione.connections:
                try:
                    if (conn.gruppo == connessione.gruppo
                    and str(conn.playlist_id) == str(connessione.playlist_id)
                    and str(conn.device_id) == str(connessione.device_id)
                    and conn.tipologia == "browser_conference"):

                        connessione.send_composed_message(conn, message)
                except:
                    pass


def send_direct_message(connessione, message_content_to_send, recipient="browser"):
    # send a message directly to the specified browser

    if recipient == "browser_conference":

        message = {}

        message_sender = {}
        message_sender['id'] = connessione.id
        message_sender['type'] = connessione.tipologia

        message_recipient = {}
        message_recipient['id'] = connessione.gruppo
        message_recipient['type'] = "browser"

        message['message_content'] = message_content_to_send
        message['message_sender'] = message_sender
        message['message_recipient'] = message_recipient

        connessione.send_composed_message(connessione, message)


def compose_message(text, content):
    # compose results in json format
    message_content = {}
    message_content['type'] = "json"
    message_content['message'] = text
    message_content['json'] = content
    return message_content
