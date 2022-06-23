# TODO: Refactor

import secrets
import socket

import argparse
import logging

from foundations.connection import Connection
from tasks import GoingElectric, CSExplorer, CSAirline, CS2521_Lab1_1, CS2521_Lab1_2, CS1511_22T2_Asm0, CS2521_Lab2_1, CS2521_Lab2_2

# zID WhiteList
WHITELIST = []

logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)s] %(asctime)s \t%(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S')


parser = argparse.ArgumentParser(description='Cloud-Autotest Worker.')
parser.add_argument('--host', type=str, nargs=1, default=['0.0.0.0'],
                    required=False,
                    help="The host to bind to.")
parser.add_argument('--port', type=int, nargs=1, default=[15000],
                    required=False,
                    help="The port to bind to.")

args = parser.parse_args()

host = args.host[0]
port = args.port[0]

logging.info('Starting server...')
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

server.bind((host, port))
server.listen(5)
logging.info(f'Listening on {host}:{str(port)}.')


class ServerContext():
    def __init__(self, socketConn) -> None:
        self.connection = Connection(socketConn)
        self.connection.start()
        self.connection.registerEventListener('hello', self.handleHello)
        self.taskId = None
        self.workerId = None
        self.task = None

    def handleHello(self, data):
        taskId = data['taskId'] if 'taskId' in data else None
        workerId = data['workerId'] if 'workerId' in data else None
        workerType = data['workerType'] if 'workerType' in data else 'tester'
        if taskId is None:
            self.dropConnection('No taskId provided.')
            return

        self.taskId = taskId
        if taskId not in TASKS_AVAILABLE:
            self.dropConnection('TaskId not found.')
            return
        zId = data['zId'] if 'zId' in data else None
        if zId is None:
            self.dropConnection('Failed to start autotest due to an error.')
            return
        if zId not in WHITELIST:
            self.dropConnection('Failed to start autotest due to an error.')
            return

        if workerType == 'tester':
            self.workerId = workerId if workerId else secrets.token_hex(16)
            self.task = TASKS_AVAILABLE[taskId].newTaskRunner(
                connection=self.connection, workerId=self.workerId)
            self.connection.fire('ack', {
                'workerId': self.workerId
            })
        elif workerType == 'api':
            self.workerId = workerId if workerId else secrets.token_hex(16)
            self.task = TASKS_AVAILABLE[taskId].newTaskApi(
                connection=self.connection, workerId=self.workerId)
            self.connection.fire('ack', {
                'workerId': self.workerId
            })

    def dropConnection(self, withReason='Dropped.'):
        self.connection.fire("drop", {
            'reason': withReason
        })
        self.connection.close()


TASKS_AVAILABLE = {
    'going_electric': GoingElectric(),
    'cs2521_lab1_1': CS2521_Lab1_1(),
    'cs2521_lab1_2': CS2521_Lab1_2(),
    'cs2521_lab2_1': CS2521_Lab2_1(),
    'cs2521_lab2_2': CS2521_Lab2_2(),
}


while True:
    sx, addr = server.accept()
    ServerContext(sx)
