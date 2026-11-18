"""Stałe integracji Thesla Green ModBUS."""

DOMAIN = "thesla_green_modbus"

CONF_NAME = "name"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_TIMEOUT = "timeout"
CONF_DELAY = "delay"
CONF_SLAVE = "slave"
CONF_ENTITIES = "entities"
CONF_TYPE = "connection_type"
CONF_MSG_WAIT = "message_wait_ms"
CONF_SERIAL_PORT = "serial_port"
CONF_BAUDRATE = "baudrate"
CONF_BYTESIZE = "bytesize"
CONF_PARITY = "parity"
CONF_STOPBITS = "stopbits"
CONF_METHOD = "method"

TYPE_TCP = "tcp"
TYPE_RTUOVERTCP = "rtuovertcp"
TYPE_UDP = "udp"
TYPE_SERIAL = "serial"
NETWORK_TYPES = (TYPE_TCP, TYPE_RTUOVERTCP, TYPE_UDP)

DEFAULT_BAUDRATE = 9600
DEFAULT_BYTESIZE = 8
DEFAULT_PARITY = "even"
DEFAULT_STOPBITS = 1
DEFAULT_METHOD = "rtu"
# wg dokumentacji HA: 30 ms dla serial, 0 dla pozostałych
DEFAULT_MSG_WAIT_SERIAL = 30
DEFAULT_MSG_WAIT_NETWORK = 0

DEFAULT_NAME = "Rekuperator"
DEFAULT_HOST = "192.168.0.11"
DEFAULT_PORT = 502
DEFAULT_TIMEOUT = 5
DEFAULT_DELAY = 2
DEFAULT_SLAVE = 9

# Maksymalny strumień powietrza (m3/h) używany do wyliczenia wysterowania w %
MAX_FLOW = 240
# Pojemność cieplna powietrza [J/(m3*K)] używana do wyliczenia mocy
AIR_HEAT_CAPACITY = 1200

# Co ile sekund coordinator sprawdza, które rejestry są "do odpytania"
TICK_SECONDS = 1
# Po ilu kolejnych nieudanych odczytach rejestru encja staje się niedostępna
MAX_READ_FAILS = 3
