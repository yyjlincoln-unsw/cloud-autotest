from foundations import SimpleTask, SimpleTaskRunner
import random

from foundations.tasks.simpletask import SimpleTaskApi


class CS2521_Lab2_2(SimpleTask):
    # Sorted Insert
    def __init__(self):
        super().__init__(CS2521_Lab2_2_Runner, CS2521_Lab2_2_Api)

    def _generateNewInput(self):
        commands = []
        # Setup
        numOfCommands = random.randint(5,100)
        for _ in range(numOfCommands):
            cmdType = random.choice(['+','-','f','s'])
            if cmdType == '+':
                for x in range(random.randint(1, 100)):
                    numToEnqueue = random.randint(-1000,1000)
                    commands.append(f'+ {numToEnqueue}')
            elif cmdType == '-':
                for x in range(random.randint(1, 100)):
                    commands.append('-')
            elif cmdType == 'f':
                commands.append('f')
            elif cmdType == 's':
                commands.append('s')
        commands.append('q')
        return '\n'.join(commands)


class CS2521_Lab2_2_Runner(SimpleTaskRunner):
    def _run(self, nextInputId, nextInput):
        self.stdin(nextInput)
        self.eof()


class CS2521_Lab2_2_Api(SimpleTaskApi):
    'No modification to the SimpleTaskApi'
    pass
