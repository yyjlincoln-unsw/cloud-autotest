from . import GenericTask, GenericTaskRunner, GenericTaskApi
import secrets
from ..connection import Connection
from threading import Lock
import logging


class SimpleTask(GenericTask):
    def __init__(self, taskRunnerClass, apiClass=None):
        self.inputIdInOrder = []  # [inputId], in order
        self.inputIdToInput = {}  # inputId -> input
        self.inputIdToOutputToWorkerIds = {}  # inputId -> output -> [workerID]
        self.workerIdToInputIdToOutput = {}  # workerId -> inputId -> output
        self.workerProgress = {}  # workerId -> progress
        self.taskRunnerClass = taskRunnerClass
        self.writeLock = Lock()
        self.apiClass = apiClass

    def awaitNewInput(self):
        self.generateNewInput()

    def _generateNewInput(self):
        'Override this'
        raise NotImplementedError()

    def generateNewInput(self):
        newInput = self._generateNewInput()
        inputId = secrets.token_hex(16)
        self.inputIdInOrder.append(inputId)
        self.inputIdToInput[inputId] = newInput
        self.inputIdToOutputToWorkerIds[inputId] = {}

    def newTaskRunner(self, connection, workerId):
        # Set the progress
        if workerId not in self.workerProgress:
            self.workerProgress[workerId] = 0
        currentProgress = self.workerProgress[workerId]
        self.writeLock.acquire()
        self.workerProgress[workerId] += 1
        self.writeLock.release()
        return self.taskRunnerClass(task=self, connection=connection,
                                    workerId=workerId,
                                    progress=currentProgress)

    def newTaskApi(self, connection, workerId):
        if self.apiClass is None:
            logging.warning("No apiClass was configrued.")
            connection.close()
            return None
        return self.apiClass(task=self, connection=connection,
                             workerId=workerId)


class SimpleTaskRunner(GenericTaskRunner):
    def __init__(self, task, connection: Connection, workerId, progress):
        self.task = task
        self.connection = connection
        self.workerId = workerId
        self.output = ''
        self.killReason = None
        self.progress = progress

        if len(task.inputIdInOrder) <= self.progress:
            self.progress = len(task.inputIdInOrder)
            # Generate a new input
            self.task.awaitNewInput()
        self.connection.registerEventListener('stdout', self.onStdout)
        self.connection.registerEventListener('appkill', self.onAppKill)
        self.connection.registerEventListener('appterm', self.onAppTerm)
        self.connection.registerEventListener('admin-control', self.onAdmin)
        self.run()

    def _run(self, nextInputId, nextInput):
        'Override this.'
        raise NotImplementedError()

    def run(self):
        nextInputId = self.task.inputIdInOrder[self.progress]
        nextInput = self.task.inputIdToInput[nextInputId]
        self._run(nextInputId=nextInputId, nextInput=nextInput)

    def onAppKill(self, data):
        self.killReason = data['reason']
        self.connection.localFire("appterm", None)
        self.connection.fire('error', {
            'message': 'Task could not be completed.',
        })

    def onAppTerm(self, data):
        currentProgress = self.progress
        inputId = self.task.inputIdInOrder[currentProgress]
        if self.output not in self.task.inputIdToOutputToWorkerIds[inputId]:
            self.task.inputIdToOutputToWorkerIds[inputId][self.output] = []
        self.task.inputIdToOutputToWorkerIds[inputId][self.output].append(
            self.workerId)
        if self.workerId not in self.task.workerIdToInputIdToOutput:
            self.task.workerIdToInputIdToOutput[self.workerId] = {}
        self.task.workerIdToInputIdToOutput[self.workerId][inputId] = \
            self.output

        # Calculate total tests
        totalTests = 0
        for output, workerIds in self.task.\
                inputIdToOutputToWorkerIds[inputId].items():
            totalTests += len(workerIds)
        sameOutput = len(
            self.task.inputIdToOutputToWorkerIds[inputId][self.output])

        self.connection.fire('report',
                             {
                                 'total': totalTests,
                                 'sameoutput': sameOutput,
                                 'similarity': sameOutput/totalTests,
                                 'output': self.output,
                                 'inputId': inputId,
                                 'input': self.task.inputIdToInput[inputId],
                                 'testNumber': currentProgress,
                                 'allOutputs': self.task.
                                 inputIdToOutputToWorkerIds[inputId]
                             })
        self.completed()

    def onStdout(self, data):
        message = data['message'].replace('\r\n', '\n')
        self.output += message

    def completed(self):
        self.connection.removeEventListener('stdout', self.onStdout)
        self.connection.removeEventListener('appkill', self.onAppKill)
        self.connection.removeEventListener('appterm', self.onAppTerm)
        self.connection.fire('completed')

    def onAdmin(self, data):
        if 'command' not in data:
            self.connection.fire('error', {
                'message': 'No command specified'
            })
            return
        command = data['command']
        if command == 'set-progress':
            if 'progress' not in data:
                self.connection.fire('error', {
                    'message': 'No progress specified'
                })
                self.completed()
                return
            if 'workerId' not in data:
                workerId = self.workerId
            else:
                workerId = data['workerId']

            progress = data['progress']
            if progress < 0 or progress > len(self.task.inputIdInOrder):
                self.connection.fire('error', {
                    'message': 'Progress out of bounds'
                })
                self.completed()
                return
            self.task.workerProgress[workerId] = progress
            self.connection.fire('message', {
                'message': f'Progress set to {progress}'
            })
        elif command == 'purge-data':
            if 'workerId' not in data:
                workerId = self.workerId
            else:
                workerId = data['workerId']
            self.task.workerProgress[workerId] = 0
            for inputId, outputToWorkerIds in self.task.\
                    inputIdToOutputToWorkerIds.items():
                for output in list(outputToWorkerIds.keys()):
                    workerIds = outputToWorkerIds[output]
                    if workerId in workerIds:
                        workerIds.remove(workerId)
                    if len(workerIds) == 0:
                        del outputToWorkerIds[output]

            if workerId in self.task.workerIdToInputIdToOutput:
                self.task.workerIdToInputIdToOutput[workerId] = {}

            self.connection.fire('message', {
                'message': f'Data purged for {workerId}'
            })
        elif command == 'purge-all':
            self.task.workerProgress = {}
            self.task.inputIdToInput = {}
            self.task.inputIdToOutputToWorkerIds = {}
            self.task.workerIdToInputIdToOutput = {}
            self.task.inputIdInOrder = []

            self.connection.fire('message', {
                'message': 'Purged all data.'
            })
        elif command == 'server-statistics':
            self.connection.fire('statistics', {
                'workerProgress': self.task.workerProgress,
                'inputIdToInput': self.task.inputIdToInput,
                'inputIdToOutputToWorkerIds': self.task.
                inputIdToOutputToWorkerIds,
                'workerIdToInputIdToOutput': self.task.
                workerIdToInputIdToOutput,
                'inputIdInOrder': self.task.inputIdInOrder
            })
        else:
            self.connection.fire('error', {
                'message': f'Unknown command {command}'
            })
        self.completed()


class SimpleTaskApi(GenericTaskApi):
    def __init__(self, task, connection, workerId):
        super().__init__(task, connection, workerId)
        self.connection.registerEventListener(
            'get-input-by-id', self.getInputById)

    def getInputById(self, data):
        if 'inputId' not in data:
            self.connection.fire('input', {
                'input': None
            })
            self.connection.fire('error', {
                'message': 'No inputId specified'
            })
            return
        if data['inputId'] not in self.task.inputIdToInput:
            self.connection.fire('input', {
                'input': None
            })
            self.connection.fire('error', {
                'message': 'Unknown inputId'
            })
            return
        self.connection.fire('input', {
            'input': self.task.inputIdToInput[data['inputId']]
        })
