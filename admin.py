import socket
import argparse
import time
from foundations import Connection
import getpass

parser = argparse.ArgumentParser(description='Cloud-Autotest Admin.')
parser.add_argument('--host', type=str, nargs=1, default=['server.cloudtest.yyjlincoln.app'],
                    help="The host to connect to.")
parser.add_argument('--port', type=int, nargs=1, default=[15000],
                    help="The port to connect to.")
parser.add_argument('--taskId', type=str, nargs=1, required=True,
                    help="The task id.")
parser.add_argument('--workerId', type=str, nargs=1, required=False,
                    help="The target workerId.")
parser.add_argument('--set-progress', type=int, nargs=1, required=False,
                    help="Set progress to.")
parser.add_argument('--purge-data', action='store_true',
                    default=False,
                    help="Purge data for workerId specified in --workerId.")
parser.add_argument('--purge-all', action='store_true',
                    default=False,
                    help="Purges all data.")
parser.add_argument('--server-statistics', action='store_true',
                    default=False,
                    help="Purges all data.")


args = parser.parse_args()
host = args.host[0]
port = args.port[0]
taskId = args.taskId[0] if args.taskId else None
workerId = args.workerId[0] if args.workerId else None
setProgress = args.set_progress[0] if args.set_progress else None
purgeData = args.purge_data
purgeAll = args.purge_all
serverStatistics = args.server_statistics

if setProgress is None and not purgeData and not purgeAll and \
        not serverStatistics:
    raise Exception("No flag was set.")

s = socket.socket()
s.connect((host, port))

connection = Connection(s)
completed = False


class AdminContext():
    def __init__(self, connection: Connection) -> None:
        self.connection = connection
        connection.registerEventListener('ack', self.handleACK)
        connection.registerEventListener('error', self.handleError)
        connection.registerEventListener('message', self.handleMessage)
        connection.registerEventListener('completed', self.completed)
        connection.registerEventListener('drop', self.onDrop)
        connection.registerEventListener('statistics', self.onStatistics)
        connection.start()

        connection.fire('hello', {
            'taskId': taskId,
            'workerId': 'admin-control-worker',
            "zId": getpass.getuser()
        })

    def handleACK(self, data):
        print('The server has acknowledged the connection.')
        # Now handle the events.
        if purgeData:
            connection.fire('admin-control', {
                'command': 'purge-data',
                'workerId': workerId,
            })
        if setProgress is not None:
            connection.fire('admin-control', {
                'workerId': workerId,
                'progress': setProgress,
                'command': 'set-progress',
            })
        if purgeAll:
            connection.fire('admin-control', {
                'command': 'purge-all',
            })
        if serverStatistics:
            connection.fire('admin-control', {
                'command': 'server-statistics',
            })

    def handleError(self, data):
        print("ERROR:", data['message'])

    def handleMessage(self, data):
        print(data['message'])

    def onDrop(self, data):
        global completed
        print('Connection was dropped:', data['reason'])
        completed = True

    def onStatistics(self, data):
        print(data)

    def completed(self, data):
        global completed
        completed = True


AdminContext(connection)
while not completed:
    time.sleep(0.1)
