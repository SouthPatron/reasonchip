class ClientException(Exception):
    pass


class ConnectionException(ClientException):
    pass


class BadPacketException(ClientException):
    pass


class UnsupportedPacketTypeException(ClientException):
    pass


class NoCapacityException(ClientException):
    pass


class CookieNotFoundException(ClientException):
    pass


class CookieCollisionException(ClientException):
    pass


class BrokerWentAwayException(ClientException):
    pass


class WorkerWentAwayException(ClientException):
    pass


class RemoteException(ClientException):
    pass
