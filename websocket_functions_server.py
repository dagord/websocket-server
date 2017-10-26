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
Strimy server
'''

from devices.models import Dispositivi, DispositiviLogs
from django.core.mail import send_mail
from django.conf import settings


def send_command(connessione, message_content):

    if 'type' not in message_content:
        message_content['type'] = ""

    if message_content['type'] == "log":
        try:
            dispositivo_log = DispositiviLogs()
            dispositivo_log.id_dispositivo_id = connessione.device_pk
            dispositivo_log.activation_key = connessione.device_id
            dispositivo_log.ugrp_id_group_id = connessione.gruppo
            dispositivo_log.log = message_content['message']
            dispositivo_log.save()
        except:
            pass


def send_disconnected_message(device_id, update_time):
    dispositivo = Dispositivi.objects.filter(activation_key=device_id)
    if len(dispositivo)>0:
        dispositivo = dispositivo.get()
        admin_mail = dispositivo.admin_contact()

        message = "Player went offline!<br><br>"
        message += "activation key: <b>%s</b><br>" % device.id
        message += "description: <b>%s</b><br>" % dispositivo.descrizione
        message += "last online: <b>%s</b><br>" % update_time

        # the client dropped connection, so system admin must be notified
        for admin_mail_temp in admin_mail:

            try:
                # send mail to admin
                send_mail(
                    'Strimy: player offline',
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [admin_mail_temp],
                    fail_silently=False,
                    html_message=message,
                )
            except:
                pass
