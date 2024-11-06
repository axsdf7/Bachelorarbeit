from Library import clients


"""
Parameter:
param send_freq [Hz]: Frequenz, mit der Nachrichten gesendet werden sollen
broadcast_port: Port des Broadcasts (muss übereinstimmen mit Server_start)
logger_name: Name des Loggers
"""

# Setup
freq = 100
broadcast_port = 50001
logger_name = "client.log"
logger = clients.create_logger(logger_name)

# Start
clients.start(logger, freq, broadcast_port)
