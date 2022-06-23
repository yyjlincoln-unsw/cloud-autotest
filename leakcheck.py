import getpass
import subprocess
import socket
from foundations import Connection
import logging
from sys import exit
VERSION = '0.1b'

DEFAULT_HOST = 'server.cloudtest.yyjlincoln.app'
DEFAULT_PORT = 15000

logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)s] %(asctime)s \t%(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S')


def execute_command(command, stdin=None):
    process = subprocess.Popen(
        command.split(' '), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE)
    if stdin:
        process.stdin.write(stdin.encode())
    process.stdin.close()
    output = ''
    while process.poll() is None:
        try:
            process.stdout.flush()
        except Exception:
            break
        output += process.stdout.readline().decode('utf-8')
    output += process.stdout.read().decode('utf-8')
    return output


print('')
print('==========')
print('CS Airline Leak Check Tool')
print(f'Version {VERSION} - @yyjlincoln')
print('Feedback? cs-airline-leakcheck.unsw@yyjlincoln.app')
print('\nCompiling with dcc...')
compileCommand = 'dcc cs_airline.c manifest.c -o cs_airline --valgrind --leakcheck'
compileOutput = execute_command(compileCommand)
if compileOutput:
    print('Compilation failed.')
    print(compileOutput)
    exit(1)


def check(commands):
    'Returns True if the test was passed.'
    commands = commands.strip().split('\n')

    found = False
    nCmd = int(commands[0])
    for lineNum in range(len(commands)+1):
        e = lineNum + 1
        cmd = commands[0:lineNum]
        if lineNum < len(commands) and commands[lineNum] not in ['print', 'subroute', 'change_origin', 'bypass', 'emergency',
                                                                 'cancel', 'reverse', 'add_person', 'print_manifest', 'stats']:
            #  Skip the line as the next line is not an opcode - hence this line is data.
            continue
        if lineNum <= nCmd:
            continue
        if e <= len(commands):
            print(
                f"Testing line {lineNum}, before command {commands[e-1]} - ", end='', flush=True)
        else:
            print("Testing the last line - ", end='', flush=True)
        rst = execute_command('./cs_airline', '\n'.join(cmd))
        if 'Error: free not called for memory allocated' in rst:
            print('failed.\n', flush=True)
            print(rst)
            print(
                f'Line {lineNum-1} of the input is the first line that produces a memory leak.')
            for x in range(len(commands)):
                if x == lineNum-1:
                    print(f'--> {commands[x]}')
                else:
                    print(f'    {commands[x]}')
            found = True
            break
        else:
            print('passed.', flush=True)

    if not found:
        print('No memory leak found.')

    return not found


class ApiCtx:
    def __init__(self, conn, taskId) -> None:
        self.connection = Connection(conn)
        self.connection.start()
        self.connection.registerEventListener('error', self.onError)
        self.connection.registerEventListener('drop', self.onDrop)
        self.connection.fire("hello", {
            'taskId': taskId,
            'workerId': 'leakcheck',
            'zId': getpass.getuser(),
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
    print('Starting the leak autotest...')
    taskId = input('TaskId: ')
    inputId = input('InputId: ')
    s = socket.socket()
    host = DEFAULT_HOST
    port = DEFAULT_PORT
    print('You will be connecting to: ' +
          host + ':' + str(port))
    differentServer = input(
        '\nDo you want to specify a different host/port? [y/N]: ').lower() == 'y'
    if differentServer:
        host = input('Host: ')
        port = int(input('Port: '))
    s.connect((host, port))
    ctx = ApiCtx(s, taskId=taskId)
    try:
        commands = ctx.getInputById(inputId=inputId)
        if not commands:
            print('Could not fetch the commands')
            return
        print('Starting...')
        check(commands)
    except Exception:
        raise


main()
