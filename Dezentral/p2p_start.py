from Library import p2p


"""
Parameter:
send_freq [Hz]: Frequenz, mit der Nachrichten gesendet werden sollen
bc_interval [s]: Sendet Broadcast-Nachricht alle 'bc_interval' Sekunden
timeout [s]: Nach Ablauf dieser Zeit wird der Kommunikationsteilnehmer aus der Liste aller Teilnehmer entfernt und 
muss sich erneut melden (hier 2x bc_interval)
c_port: Port für die Kommunikation
logger_name: Name des Loggers, in dem Informationen gespeichert werden
"""


# Setup
send_freq = 20
bc_time = 5
timeout = 2*bc_time
c_port = 5006
logger_name = "p2p.log"
logger = p2p.create_logger(logger_name)

# Start
p2p.start(logger, send_freq, c_port, timeout, bc_time)
