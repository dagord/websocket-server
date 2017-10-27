# Websocket server for Strimy

Strimy is a cloud based digital signage service that uses Raspberry as remote players for broadcasting multimedia content on tv/monitors.
Strimy backend is entirely developed on Django framework so you'll need a full installation to run the script: it has been published on Github only for demo purposes.

For more informations on Strimy project please refer to: http://strimy.tv

This server relies on over Autobahn/Twisted; it's used to exchange communications between Strimy server and remote clients.

**websocket_server.py** - core script  
**websocket_functions_server.py** - this modules provides the interaction with Strimy server  
**websocket_functions_browser.py** - this modules provides the interaction with Strimy users (browsers)  
**websocket_functions_device.py** - this modules provides the interaciton with Strimy digital signage" players  
**websocket_functions_device_conference.py** - this modules provides the interaction with Strimy "conference box" players  



