class GenericTask():
    def __init__(self):
        pass

    def newTaskRunner(self, connection, workerId):
        return GenericTaskRunner(task=self, connection=connection,
                                 workerId=workerId)

    def newTaskApi(self, connection, workerId):
        return GenericTaskApi(task=self, connection=connection,
                              workerId=workerId)


class GenericTaskApi():
    def __init__(self, task, connection, workerId):
        self.task = task
        self.connection = connection
        self.workerId = workerId


class GenericTaskRunner(GenericTask):
    def __init__(self, task, connection, workerId):
        self.task = task
        self.connection = connection
        self.workerId = workerId

    def stdin(self, message):
        self.connection.fire('stdin', {
            'message': message
        })

    def eof(self):
        self.connection.fire('eof')

    def message(self, message):
        self.connection.fire('message', {
            'message': message
        })

    def completed(self):
        self.connection.fire('completed')
