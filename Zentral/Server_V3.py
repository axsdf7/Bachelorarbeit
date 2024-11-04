from Library import server


# Setup
server_port = 50000
broadcast_port = 50001
logger_name = "server.log"
logger = server.create_logger(logger_name)

# Start
server.start(logger, server_port, broadcast_port)
