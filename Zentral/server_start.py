from Library import server


"""
Parameter:
broadcast_port: Port des Broadcasts, muss mit client_start übereinstimmen!
server_port: Port des Servers
broadcast_interval [s]: Sendet alle [broadcast_interval] Sekunden eine Broadcast-Nachricht an alle Teilnehmer mit 
IP-Adresse und Port des Servers
logger_name: Name des Loggers, in dem alle Serverdaten gespeichert werden
"""

# Setup
broadcast_port = 50001
server_port = 50000
broadcast_interval = 5
logger_name = "server.log"
logger = server.create_logger(logger_name)

# Start
server.start(logger, server_port, broadcast_port, broadcast_interval)
