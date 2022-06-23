from foundations import SimpleTask, SimpleTaskRunner
import random

from foundations.tasks.simpletask import SimpleTaskApi


class CS2521_Lab1_2(SimpleTask):
    # Sorted Insert
    def __init__(self):
        super().__init__(CS2521_Lab1_2_Runner, CS2521_Lab1_2_Api)

    def _generateNewInput(self):
        commands = []
        numOfNumbers = random.randint(0, 1000)
        commands.append(' '.join([str(random.randint(-1000, 1000))
                        for _ in range(numOfNumbers)]))
        return '\n'.join(commands)


class CS2521_Lab1_2_Runner(SimpleTaskRunner):
    def _run(self, nextInputId, nextInput):
        self.stdin(nextInput)
        self.eof()


class CS2521_Lab1_2_Api(SimpleTaskApi):
    'No modification to the SimpleTaskApi'
    pass
