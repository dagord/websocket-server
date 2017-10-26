'''
funzioni relative all'interazione col device
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

            if (conn.gruppo == connessione.gruppo or connessione.amministratore == 1) and conn.tipologia[0:6] == "device" and str(conn.device_id) == str(message['message_recipient']['id']):
                connessione.send_composed_message(conn, message)
                device_connesso = 1

        if device_connesso == 0 and message_content_to_send['type'] == "json":
            comandi_websocket_save(
                message_recipient['id'], message_sender['id'],
                message_content_to_send['message'],
                message_content_to_send['json']
                )


def get_messages(connessione):
    # verifica se ci sono comandi in coda inviati dal server mentre il device era disconnesso
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
