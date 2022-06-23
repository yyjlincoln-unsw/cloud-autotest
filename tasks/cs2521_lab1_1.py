from foundations import SimpleTask, SimpleTaskRunner
import random

from foundations.tasks.simpletask import SimpleTaskApi


class CS2521_Lab1_1(SimpleTask):
    # Sorted Insert
    def __init__(self):
        super().__init__(CS2521_Lab1_1_Runner, CS2521_Lab1_1_Api)

    def _generateNewInput(self):
        commands = []
        # Setup
        numOfNumbers = random.randint(0, 1000)
        # Sorted Numbers
        commands.append(' '.join([str(i) for i in sorted([random.randint(-1000, 1000)
                        for i in range(numOfNumbers)])]))
        commands.append(str(random.randint(-1500, 1500)))
        return '\n'.join(commands)


class CS2521_Lab1_1_Runner(SimpleTaskRunner):
    def _run(self, nextInputId, nextInput):
        self.stdin(nextInput)
        self.eof()


class CS2521_Lab1_1_Api(SimpleTaskApi):
    'No modification to the SimpleTaskApi'
    pass
