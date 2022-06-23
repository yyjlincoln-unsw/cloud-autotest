from foundations import SimpleTask, SimpleTaskRunner
import random


class GoingElectric(SimpleTask):
    def __init__(self):
        super().__init__(GoingElectricRunner)

    def _generateNewInput(self):
        i = []
        # Initial
        i.append(str(random.randint(0, 5)))
        for x in range(random.randint(5, 15)):
            randSeed = random.randint(0, 4)
            if randSeed == 0:
                i.append(str(0))
            elif randSeed == 1:
                i.append(str(random.randint(0, 2)))
            elif randSeed == 2:
                i.append(str(random.randint(3, 5)))
            elif randSeed == 3:
                i.append(str(random.randint(0, 10)))
            elif randSeed == 4:
                i.append(str(random.randint(0, 5)))
        return ' '.join(i)


class GoingElectricRunner(SimpleTaskRunner):
    def _run(self, nextInputId, nextInput):
        self.stdin(nextInput)
        self.eof()
