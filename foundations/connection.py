import json
import threading
import logging
import secrets
import time
# Type of waitEvents:
# "eventName" : {
#   "id": <waiterId>,
#   "captured": bool,
# }


class Disconnected(Exception):
    'Disconnected.'


class Connection():
    def __init__(self, conn, initialBuffer=b'') -> None:
        self.conn = conn
        self.buffer = initialBuffer
        self.eventHandlers = {}
        self.pastEvents = {}
        self.waitEvents = {}
        self.waiter = {}
        self.connected = True

    def start(self):
        t = threading.Thread(target=self.recvLoop)
        t.setDaemon(True)
        t.start()

    def registerEventListener(self, event, listener):
        'Special keyword: disconnect. Fired when the connection is closed.'
        if event not in self.eventHandlers:
            self.eventHandlers[event] = [listener]
            if event in self.pastEvents:
                for data in self.pastEvents[event]:
                    self.localFire(event, data)
                del self.pastEvents[event]
        else:
            self.eventHandlers[event].append(listener)

    def removeEventListener(self, event, listener):
        if event not in self.eventHandlers:
            return
        if listener not in self.eventHandlers[event]:
            return
        self.eventHandlers[event].remove(listener)

    def handleEventMessage(self, message):
        try:
            message = json.loads(message)
            assert 'type' in message
            assert 'data' in message
        except json.JSONDecodeError:
            logging.debug(
                f'Worker received invalid JSON: {message}; \
ignoring.')
            return
        except AssertionError:
            logging.debug(
                f'Worker received invalid JSON: {message}; \
ignoring.')
            return

        eventType = message['type']
        data = message['data']
        self.localFire(eventType, data)

    def handleBufferContent(self):
        bufferSplit = self.buffer.split(b'\n')
        if len(bufferSplit) > 1:
            self.handleEventMessage(bufferSplit[0])
            self.buffer = b'\n'.join(bufferSplit[1:])
        else:
            return
        self.handleBufferContent()

    def localFire(self, event, data):
        if not self.preLocalFire(event, data):
            return
        if event in self.eventHandlers:
            for handler in self.eventHandlers[event]:
                handler(data)
        else:
            if event not in self.pastEvents:
                self.pastEvents[event] = []
            self.pastEvents[event].append(data)

    def recvLoop(self):
        while True:
            self.handleBufferContent()
            try:
                data = self.conn.recv(2048)
                if data == b'':
                    logging.debug('Connection closed.')
                    self.connected = False
                    self.localFire('disconnect', None)
                    return
                self.buffer += data
            except Exception:
                logging.debug('Connection closed.')
                self.connected = False
                self.localFire('disconnect', None)
                return

    def fire(self, event, data=None):
        if not self.connected:
            return
        message = json.dumps({'type': event, 'data': data})
        try:
            self.conn.send(message.encode('utf-8') + b'\n')
        except Exception:
            pass

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def preLocalFire(self, event, data):
        if event in self.waitEvents:
            captured = self.waitEvents[event]['captured']
            waiterId = self.waitEvents[event]['id']
            self.waiter[waiterId] = data
            del self.waitEvents[event]
            if captured:
                return False
        return True

    def waitFor(self, event, capture=True):
        if event in self.waitEvents:
            logging.warning('Already waiting for event:', event)
            return
        waiterId = secrets.token_hex(8)
        self.waitEvents[event] = {
            'id': waiterId,
            'captured': capture
        }
        while waiterId not in self.waiter and self.connected:
            time.sleep(0.05)
        if waiterId not in self.waiter:
            raise Disconnected("Disconnected.")

        data = self.waiter[waiterId]
        del self.waiter[waiterId]
        return data
