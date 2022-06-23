import time
import subprocess
import socket
import argparse
import threading
import colorama
from foundations import Connection
from sys import exit
import getpass

# TODO - Do not purge data when resetting the progress.
# Let the server handle it.

logFile = None


class AdminContext():
    def __init__(self, socketConn, taskId: str) -> None:
        self.connection = Connection(socketConn)
        self.connected = False
        self.completed = False

        self.connection.registerEventListener('ack', self.handleACK)
        self.connection.registerEventListener('error', self.handleError)
        self.connection.registerEventListener('message', self.handleMessage)
        self.connection.registerEventListener('completed', self.onCompleted)
        self.connection.registerEventListener('drop', self.onDrop)
        self.connection.registerEventListener('statistics', self.onStatistics)
        self.connection.start()

        self.connection.fire('hello', {
            'taskId': taskId,
            'workerId': 'admin-control-worker',
            'zId': getpass.getuser()
        })
        print('Logging in to the server...')

    def handleACK(self, data):
        self.connected = True

    def handleError(self, data):
        print("Error:", data['message'])

    def handleMessage(self, data):
        print(data['message'])

    def onDrop(self, data):
        print('Error:', data['reason'])
        self.completed = True

    def onStatistics(self, data):
        print(data)

    def onCompleted(self, data):
        self.completed = True

    def purgeData(self, workerId):
        self.connection.fire('admin-control', {
            'command': 'purge-data',
            'workerId': workerId,
        })

    def setProgress(self, workerId, progress):
        self.purgeData(workerId)
        self.connection.fire('admin-control', {
            'workerId': workerId,
            'progress': progress,
            'command': 'set-progress',
        })

    def purgeAll(self):
        self.connection.fire('admin-control', {
            'command': 'purge-all',
        })

    def serverStatistics(self):
        self.connection.fire('admin-control', {
            'command': 'server-statistics',
        })


class TaskContext():
    def __init__(self, socketConn, taskId, workerId, file,
                 host=None, port=None):
        self.connection = Connection(socketConn)
        self.taskId = taskId
        self.workerId = workerId
        self.file = file
        self.process = None
        self.completed = False
        self.dropped = False
        self.file = file
        self.host = host
        self.port = port
        self.started = 0

        self.connection.registerEventListener('ack', self.handleACK)
        self.connection.registerEventListener('stdin', self.onStdin)
        self.connection.registerEventListener('appterm', self.appTerm)
        self.connection.registerEventListener('drop', self.onDrop)
        self.connection.registerEventListener('error', self.onError)
        self.connection.registerEventListener('message', self.onMessage)
        self.connection.registerEventListener('completed', self.onCompletion)
        self.connection.registerEventListener('report', self.onReport)
        self.connection.registerEventListener('eof', self.onEOF)
        self.connection.registerEventListener('disconnect', self.onDisconnect)

    def start(self) -> bool:
        'Returns whether the test was successful.'
        self.process = subprocess.Popen(self.file.split(' '),
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        stdin=subprocess.PIPE)
        self.connection.start()
        self.onConnection()
        self.started = time.time()
        # Timeout guard
        timeoutGuardThread = threading.Thread(target=self.appTimeoutGuard)
        timeoutGuardThread.daemon = True
        timeoutGuardThread.start()
        # Send stdout to server
        stdoutThread = threading.Thread(target=self.stdoutMonitor)
        stdoutThread.daemon = True
        stdoutThread.start()
        while not self.completed:
            time.sleep(0.1)
        # We drop the connection on error - so if it's not dropped, then it's
        # successful.
        return not self.dropped

    def stdoutMonitor(self):
        while self.process.poll() is None:
            try:
                self.process.stdin.flush()
                self.process.stdout.flush()
            except Exception:
                break
            self.sendStdout(self.process.stdout.readline().decode('utf-8'))
        self.sendStdout(self.process.stdout.read().decode('utf-8'))
        self.appTerm()
        try:
            self.process.stdin.close()
            self.process.stdout.close()
            self.process.stderr.close()
        except Exception:
            pass

    def handleACK(self, data):
        workerId = data['workerId']
        self.workerId = workerId

    def dropConnection(self, withReason='Dropped.'):
        self.connection.fire("drop", {
            'reason': withReason
        })
        self.connection.close()

    def onStdin(self, data):
        message = data['message']
        try:
            self.process.stdin.write(message.encode('utf-8'))
            self.process.stdin.flush()
        except Exception:
            self.appTerm('Failed to write to stdin.')

    def onEOF(self, data):
        try:
            self.process.stdin.close()
        except Exception:
            print('Failed to close stdin.')

    def sendStdout(self, message):
        self.connection.fire('stdout', {
            'message': message
        })

    def onConnection(self):
        # Send the taskId
        self.connection.fire('hello', {
            'taskId': self.taskId,
            'workerId': self.workerId,
            'zId': getpass.getuser()
        })

    def onDisconnect(self, _):
        self.dropped = True
        self.completed = True
        self.process.kill()

    def appTerm(self, reason='Terminated.'):
        self.connection.fire('appterm', {
            'workerId': self.workerId,
            'reason': reason
        })

    def onDrop(self, data):
        self.dropped = True
        self.completed = True
        self.process.kill()
        print(data['reason'])
        exit(1)

    def onError(self, data):
        global completed, dropped
        self.dropped = True
        self.completed = True
        self.process.kill()
        print('Error:', data['message'])
        exit(1)

    def onMessage(self, data):
        message = data['message']
        print(message)

    def onCompletion(self, data):
        self.completed = True
        self.process.kill()
        exit(0)

    def appKill(self, reason='Killed.'):
        self.connection.fire('appkill', {
            'workerId': self.workerId,
            'reason': reason
        })

    def onReport(self, data):
        total = data['total']
        sameoutput = data['sameoutput']
        similarity = data['similarity']
        output = data['output']
        inputData = data['input']
        inputId = data['inputId']
        testNumber = data['testNumber']
        allOutputs = data['allOutputs']
        allOutputsPopularitySorted = sorted(
            allOutputs, key=lambda k: len(allOutputs[k]), reverse=True)
        possibleOutputs = ''
        possibleOutputsWithoutColors = ''
        for poutput in allOutputsPopularitySorted:
            outputSimilarity = len(allOutputs[poutput])/total*100
            numberOfOutputs = len(allOutputs[poutput])
            possibleOutputs += f'\n{colorama.Fore.YELLOW}{numberOfOutputs} of {total} ({str(outputSimilarity)}%) produced: {colorama.Fore.RESET}' + \
                (f'{colorama.Fore.RED}[Your Output]{colorama.Fore.RESET} ' if output ==
                 poutput else '') + \
                f"{colorama.Style.DIM}({', '.join(allOutputs[poutput])}){colorama.Style.RESET_ALL}" + \
                f'\n{poutput}\n'
            possibleOutputsWithoutColors += f'\n{numberOfOutputs} of {total} ({str(outputSimilarity)}%) produced: ' + \
                (f'[Your Output] ' if output ==
                 poutput else '') + \
                f"({', '.join(allOutputs[poutput])})" + \
                f'\n{poutput}\n'

        if similarity <= 0.5:
            print(f'''
{colorama.Fore.RED}Your program failed test {str(testNumber)}.
Execution was paused as your outputs were not similar enough
with what we have in the system.
{colorama.Fore.RESET}
{colorama.Fore.CYAN}Your output:{colorama.Fore.RESET}

{output}

{colorama.Fore.CYAN}Input:{colorama.Fore.RESET}

{inputData}

{colorama.Fore.CYAN}Possible outputs:{colorama.Fore.RESET}
{possibleOutputs}
{colorama.Fore.CYAN}
TestId: {inputId}
Total number of tests: {str(total)}.
Tests with similar output as yours: {sameoutput}.
Similarity: {str(similarity*100)}%.
{colorama.Fore.RESET}
{colorama.Fore.YELLOW}
To resume testing, execute:
python3 client.py "{self.taskId}" "{self.workerId}" "{self.file}" --host "{self.host}" --port "{self.port}"

Or, if you're using the binary version:
cloud-autotest "{self.taskId}" "{self.workerId}" "{self.file}" --host "{self.host}" --port "{self.port}"
{colorama.Fore.RESET}
''')
            writeLogs(f'''
Your program failed test {str(testNumber)}.
Execution was paused as your outputs were not similar enough
with what we have in the system.

Your output:

{output}

Input:

{inputData}

Possible outputs:
{possibleOutputsWithoutColors}

Total number of tests: {str(total)}.
Tests with similar output as yours: {sameoutput}.
Similarity: {str(similarity*100)}%.
TestId: {inputId}

To resume testing, execute:
python3 client.py "{self.taskId}" "{self.workerId}" "{self.file}" --host "{self.host}" --port "{self.port}"

Or, if you're using the binary version:
cloud-autotest "{self.taskId}" "{self.workerId}" "{self.file}" --host "{self.host}" --port "{self.port}"
''')
            self.dropConnection('Outputs were not similar enough.')
            try:
                self.process.stdout.close()
                self.process.stderr.close()
                self.process.stdin.close()
                self.process.kill()
            except Exception:
                pass
            self.dropped = True
            self.completed = True
        else:
            # Calculate the colour
            colour = colorama.Fore.GREEN
            if similarity == 1:
                colour = colorama.Fore.GREEN
            elif similarity > 0.75:
                colour = colorama.Fore.BLUE
            elif similarity > 0.5:
                colour = colorama.Fore.YELLOW
            elif similarity > 0.25:
                colour = colorama.Fore.MAGENTA
            else:
                colour = colorama.Fore.RED

            print(
                f'Test {str(testNumber)} ({inputId}) passed with a similarity index of {colour}{str(similarity*100)}% ({str(sameoutput)}/{str(total)}).{colorama.Fore.RESET}')
            writeLogs(
                f'Test {str(testNumber)} ({inputId}) passed with a similarity index of {str(similarity*100)}% ({str(sameoutput)}/{str(total)}).')

    def appTimeoutGuard(self):
        while time.time()-self.started < 30:
            time.sleep(0.5)
        if self.process.poll() is None:
            print(
                f"{colorama.Fore.RED}Program was killed due to timeout.{colorama.Fore.RESET}")
            self.process.kill()
            self.appKill()


def main(taskId, workerId, file, host, port, maxTests=0):
    global logFile
    s = socket.socket()
    try:
        s.connect((host, port))
    except Exception:
        print("Error: Failed to connect to the server.")
        exit(1)

    testsConducted = 0
    ctx = TaskContext(s, taskId, workerId, file, host, port)
    while ctx.start():
        testsConducted += 1
        if maxTests > 0 and testsConducted >= maxTests:
            print("Reached maxTests - exiting.")
            writeLogs("Reached maxTests - exiting.")
            break
        ctx = TaskContext(s, taskId, workerId, file, host, port)


def interactive():
    global logFile
    options = {
        'r': 'Run autotest',
        'p': 'Set your progress',
        'c': 'Clear previous attempts',
        'q': 'Quit'
    }
    while True:
        print("\nSelect an option from below:")
        for key, value in options.items():
            print(f'{key}: {value}')
        option = input('> ')
        if option == 'r':
            file = input('Command to execute: ')
            taskId = input('Task ID: ')
            workerId = input('Worker ID: ')
            host = DEFAULT_HOST
            port = DEFAULT_PORT
            print('You will be connecting to: ' +
                  host + ':' + str(port))
            differentServer = input(
                '\nDo you want to specify a different host/port? [y/N]: ').lower() == 'y'
            if differentServer:
                host = input('Host: ')
                port = int(input('Port: '))
            maxTests = input(
                '\nHow many tests do you want to run? [Default: 0 (unlimited)]: ')
            maxTests = int(maxTests) if maxTests.isdigit() else 0
            logFile = input(
                'Log file: [Default: cloud-autotest-[timestamp].log]: ')
            if logFile == '':
                logFile = 'cloud-autotest-'+str(int(time.time()))+'.log'
            print('\nUsing log file:', logFile)

            print("Starting autotest...\n\n")
            main(taskId, workerId, file, host, port, maxTests)
            return
        elif option == 'p':
            taskId = input('Task ID: ')
            workerId = input('Worker ID: ')
            host = DEFAULT_HOST
            port = DEFAULT_PORT
            print('You will be connecting to: ' +
                  host + ':' + str(port))
            differentServer = input(
                'Do you want to specify a different host/port? (y/N): ').lower() == 'y'
            if differentServer:
                host = input('Host: ')
                port = int(input('Port: '))
            conn = socket.socket()
            try:
                conn.connect((host, port))
            except Exception:
                print("Error: Failed to connect to the server.")
                exit(1)
            progress = int(input('Progress: '))
            ctx = AdminContext(conn, taskId)
            ctx.setProgress(workerId, progress=progress)
            while not ctx.completed:
                time.sleep(0.1)
        elif option == 'c':
            taskId = input('Task ID: ')
            workerId = input('Worker ID: ')
            host = DEFAULT_HOST
            port = DEFAULT_PORT
            print('You will be connecting to: ' +
                  host + ':' + str(port))
            differentServer = input(
                'Do you want to specify a different host/port? (y/N): ').lower() == 'y'
            if differentServer:
                host = input('Host: ')
                port = int(input('Port: '))
            conn = socket.socket()
            try:
                conn.connect((host, port))
            except Exception:
                print("Error: Failed to connect to the server.")
                exit(1)
            ctx = AdminContext(conn, taskId)
            ctx.purgeData(workerId)
            while not ctx.completed:
                time.sleep(0.1)
        elif option == 'q':
            exit(0)
        else:
            print("Invalid option. Try again.")


def writeLogs(message):
    global logFile
    if logFile:
        try:
            with open(logFile, 'a') as f:
                f.write(message + '\n')
        except Exception:
            print("Error: Failed to write to log file.")
            print("Disabling logging.")
            logFile = None


colorama.init()

DEFAULT_HOST = 'server.cloudtest.yyjlincoln.app'
DEFAULT_PORT = 15000

parser = argparse.ArgumentParser(
    description='Cloud-Autotest Worker.')
parser.add_argument('taskId', type=str, nargs=1,
                    help="The task id.")
parser.add_argument('workerId', type=str, nargs=1,
                    help="The worker id to resume tests from. \
You have to remember the workerId. Try using your name or zID.")
parser.add_argument('--host', type=str, nargs=1,
                    default=[DEFAULT_HOST],
                    help="The host to connect to.")
parser.add_argument('--port', type=int, nargs=1, default=[DEFAULT_PORT],
                    help="The port to connect to.")
parser.add_argument('--max', type=int, nargs=1, default=[0],
                    help="Maximum number of tests before exiting.")
parser.add_argument('--logFile', type=str, nargs=1, default=[None],
                    help="Maximum number of tests before exiting.")
parser.add_argument('file', type=str, nargs=1,
                    help="The file to be executed.")

try:
    args = parser.parse_args()
except SystemExit:
    print("\nEntering interactive mode.")
    try:
        interactive()
        exit(0)
    except EOFError:
        exit(0)
    except KeyboardInterrupt:
        print("\nExiting.")
        exit(0)

file = args.file[0]
host = args.host[0]
port = args.port[0]
taskId = args.taskId[0] if args.taskId else None
workerId = args.workerId[0] if args.workerId else None
logFile = args.logFile[0] if args.logFile else None
maxTests = args.max[0]

try:
    main(taskId, workerId, file, host, port, maxTests)
except KeyboardInterrupt:
    print("\nExiting.")
    exit(0)
