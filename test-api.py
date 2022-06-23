import socket
from foundations import Connection


class ApiCtx:
    def __init__(self, conn) -> None:
        self.connection = Connection(conn)
        self.connection.start()
        self.connection.registerEventListener('error', self.onError)
        self.connection.registerEventListener('drop', self.onDrop)
        self.connection.fire("hello", {
            'taskId': 'cs_airline',
            'workerId': 'test',
            'zId': 'z5423219',
            'workerType': 'api'
        })

    def onError(self, data):
        print(data['message'])

    def onDrop(self, data):
        print('Dropped: ', data)

    def getInputById(self, inputId):
        self.connection.fire('get-input-by-id', {
            'inputId': inputId
        })
        return self.connection.waitFor('input')['input']


def main():
    s = socket.socket()
    s.connect(('localhost', 15000))
    ctx = ApiCtx(s)
    print(ctx.getInputById(input('> ')))


main()
