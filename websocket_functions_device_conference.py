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
remote "conference box" Strimy players
'''

import websocket_functions_browser
from conference.models import (ConferenceCommenti, ConferenceRisposte,
                               ConferenceGiaRisposte)


def send_message(connessione, message_content_to_send):

    message = {}

    message_sender = {}
    message_sender['id'] = connessione.device_id
    message_sender['type'] = connessione.tipologia

    message_recipient = {}
    message_recipient['id'] = connessione.device_id
    message_recipient['type'] = "device_conference"

    message['message_content'] = message_content_to_send
    message['message_sender'] = message_sender
    message['message_recipient'] = message_recipient

    # checks if user is sending commands that need interaction with server
    if 'message' not in message_content_to_send:
        message_content_to_send['message'] = ""

    if message_content_to_send['message'] == "get_index":
        try:
            current_index = connessione.current_index_playlist[
                connessione.playlist_id, connessione.device_id]
        except:
            current_index = -1
        content_to_send = {}
        content_to_send['index'] = current_index
        message_content = websocket_functions_browser.compose_message(
            "set_index", content_to_send)
        websocket_functions_browser.send_direct_message(connessione,
                                                        message_content,
                                                        "browser_conference")

    elif message_content_to_send['message'] == "get_client_number":
        try:
            total_clients = connessione.users_connessi_playlist[
                connessione.playlist_id, connessione.device_id]
        except:
            total_clients = 0
        content_to_send = {}
        content_to_send['total_clients'] = total_clients
        message_content = websocket_functions_browser.compose_message(
                            "get_client_number", content_to_send)
        websocket_functions_browser.send_direct_message(
                            connessione, message_content, "browser_conference")

    elif message_content_to_send['message'] == "get_comments":
        commenti = ConferenceCommenti.objects.filter(
                    id_playlist_id=connessione.playlist_id,
                    activation_key=connessione.device_id).order_by('id')
        for commento in commenti:
            content_to_send = {}
            content_to_send['comment_id'] = commento.id
            message_content = websocket_functions_browser.compose_message(
                                "add_comment", content_to_send)
            # send comment to browser
            websocket_functions_browser.send_direct_message(connessione,
                                                            message_content,
                                                            "browser_conference")

    elif message_content_to_send['message'] == "check_answer":

        risposta = ConferenceRisposte.objects.filter(
            id_playlist_id=int(connessione.playlist_id),
            activation_key=connessione.device_id,
            indice=message_content_to_send['json']['index'],
            random_id=connessione.session_id)
        if len(risposta) > 0:
            risposta = risposta.get()
            utente_risposta = risposta.risposta
        else:
            utente_risposta = -1

        domande_gia_risposte = ConferenceGiaRisposte.objects.filter(
                id_playlist_id=int(connessione.playlist_id),
                activation_key=connessione.device_id,
                indice=message_content_to_send['json']['index'])
        if len(domande_gia_risposte) > 0:
            gia_risposta = 1
        else:
            gia_risposta = 0

        # question is already closed; retrives answer
        if gia_risposta == 1:
            array_risposte = recover_answers(
                connessione, message_content_to_send['json']['index'])
            content_to_send = {}
            content_to_send['index'] = message_content_to_send['json']['index']
            content_to_send['results'] = array_risposte
            content_to_send['answered'] = utente_risposta

            message_content = websocket_functions_browser.compose_message(
                                    "display_answer_results", content_to_send)
            # send results to browser
            for conn in connessione.connections:
                try:
                    if (conn.gruppo == connessione.gruppo
                    and str(conn.playlist_id) == str(connessione.playlist_id)
                    and str(conn.device_id) == str(connessione.device_id)
                    and conn.session_id == connessione.session_id
                    and conn.tipologia == "browser_conference"):
                        websocket_functions_browser.send_direct_message(
                            conn, message_content, "browser_conference")
                except:
                    pass

        else:  # question is stille open
            # if utente_risposta =-1 user can still answer
            message_content_to_send['json']['answered'] = utente_risposta
            websocket_functions_browser.send_message(
                connessione, message_content_to_send, "browser_conference")

    elif message_content_to_send['message'] == "send_comment":
        commento = ConferenceCommenti()
        commento.testo = message_content_to_send['json']['commento']
        commento.activation_key = connessione.device_id
        commento.id_playlist_id = connessione.playlist_id
        commento.save()
        commento_id = ConferenceCommenti.objects.latest('id').id
        content_to_send = {}
        content_to_send['comment_id'] = commento_id
        message_content = websocket_functions_browser.compose_message(
                            "add_comment", content_to_send)
        # send comment to browser
        websocket_functions_browser.send_message(connessione, message_content,
                                                 "browser_conference")
    elif message_content_to_send['message'] == "delete_single_comment":
        commento = ConferenceCommenti.objects.get(
            id_playlist_id=connessione.playlist_id,
            activation_key=connessione.device_id,
            pk=message_content_to_send['json']['comment_id'])
        commento.delete()
        content_to_send = {}
        content_to_send['index'] = message_content_to_send['json']['index']
        message_content = websocket_functions_browser.compose_message("delete_single_comment", content_to_send)
        websocket_functions_browser.send_message(connessione, message_content, "browser_conference")

    elif message_content_to_send['message'] == "get_comments":
        commenti = ConferenceCommenti.objects.filter(
            id_playlist_id=connessione.playlist_id,
            activation_key=connessione.device_id).order_by('id')
        for commento in commenti:
            content_to_send = {}
            content_to_send['comment_id'] = commento.id
            message_content = websocket_functions_browser.compose_message("add_comment", content_to_send)
            # send comment to browser
            websocket_functions_browser.send_message(connessione, message_content, "browser_conference")

    elif message_content_to_send['message'] == "send_answer":
        risposta = ConferenceRisposte.objects.filter(
            id_playlist_id=connessione.playlist_id,
            activation_key=connessione.device_id,
            indice=message_content_to_send['json']['index'],
            random_id=connessione.session_id)
        if len(risposta) > 0:
            risposta = risposta.get()
        else:
            risposta = ConferenceRisposte()
            risposta.id_playlist_id = int(connessione.playlist_id)
            risposta.activation_key = connessione.device_id
            risposta.indice = message_content_to_send['json']['index']
            risposta.random_id = connessione.session_id
        risposta.risposta = message_content_to_send['json']['answer']
        risposta.save()

    elif message_content_to_send['message'] == "send_comments_to_approve":
        commenti = ConferenceCommenti.objects.filter(
                    id_playlist_id=connessione.playlist_id,
                    activation_key=connessione.device_id).order_by('id')
        questions = []
        for commento in commenti:
            questions.append(commento.testo)
        content_to_send = {}
        content_to_send['questions'] = questions
        message_content = websocket_functions_browser.compose_message(
                            "approve_comments", content_to_send)
        # send comment to player
        send_message(connessione, message_content)

    else:
        if message_content_to_send['message'] == "approve_comments":
            commenti = ConferenceCommenti.objects.filter(
                        id_playlist_id=connessione.playlist_id,
                        activation_key=connessione.device_id).order_by('id')
            questions = []
            for commento in commenti:
                questions.append(commento.testo)
            message['message_content']['json']['questions'] = questions

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

        for conn in connessione.connections:
            if (conn.gruppo == connessione.gruppo
            and conn.tipologia == "device_conference"
            and str(conn.playlist_id) == str(connessione.playlist_id)
            and str(conn.device_id) == str(message['message_recipient']['id'])):
                connessione.send_composed_message(conn, message)


def add_client(connessione):
    if connessione.account == 0:
        try:
            connessione.users_connessi_playlist[connessione.playlist_id,
                                                connessione.device_id] += 1
        except:
            connessione.users_connessi_playlist[connessione.playlist_id,
                                                connessione.device_id] = 1
        refresh_clients(connessione, connessione.users_connessi_playlist[
            connessione.playlist_id, connessione.device_id])


def remove_client(connessione):
    if connessione.account == 0:
        try:
            connessione.users_connessi_playlist[connessione.playlist_id,
                                                connessione.device_id] -= 1
        except:
            connessione.users_connessi_playlist[connessione.playlist_id,
                                                connessione.device_id] = 0
        refresh_clients(connessione, connessione.users_connessi_playlist[
                                                connessione.playlist_id,
                                                connessione.device_id])


def refresh_clients(connessione, total_clients):
    message_content = {}
    message_json = {}
    message_json['total_clients'] = total_clients
    message_content['type'] = "json"
    message_content['message'] = "get_client_number"
    message_content['json'] = message_json
    websocket_functions_browser.send_message(connessione, message_content, "browser_conference")


def recover_answers(connessione, indice):
    # retrives the total number of answers for each question (up to 10)
    indice_risposta = 0
    array_risposte = {}
    while indice_risposta < 10:
        try:
            risposte = ConferenceRisposte.objects.filter(
                id_playlist_id=int(connessione.playlist_id),
                activation_key=connessione.device_id,
                indice=indice,
                risposta=indice_risposta)
            numero_risposte = risposte.count()
        except:
            numero_risposte = 0

        if numero_risposte > 0:
            array_risposte[indice_risposta] = numero_risposte

        indice_risposta += 1
    return array_risposte
