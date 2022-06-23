# Cloud-Autotest

Cloud-Autotest is an autotesting tool designed to compare console outputs from different implementations of the same program. It's designed with academic integrity in mind - meaning that your source code stays on your own disk, and nobody else can access it thorugh this program. For more information, refer to the security & academic integrity section.

<img width="843" alt="screenshot" src="https://user-images.githubusercontent.com/20881008/158080693-e336b631-45ed-492d-90d0-841603288ddd.png">

<img width="843" alt="screenshot" src="https://user-images.githubusercontent.com/20881008/158080790-398d41b9-26a1-4c62-b8f0-9489ef4070c6.png">



## Installation

### From source

- Install Python 3
- Clone the repository with `git clone https://github.com/yyjlincoln/cloud-autotest`
- Run it.

### Packed binary (pyinstaller)

Simply download the binary from the releases page and run it.

The binary is packed using `pyinstaller`. It may not be compatible with all platforms.

## How does it work?

Cloud-Autotest is task-based. It has the following components:

- `Task`
- `TaskRunner`

### `Connection`

A `Connection` is a wrapper class that handles the communication between the client and the server. It's event-based, and each command is packed into JSON, separated by a new line. Ideally, you should only need to use `Connection.fire`, `Connection.registerEventListener` and `Connection.removeEventListener`

### `Task`

A `Task` should be initialised at the start of the program, and it should be registered in `server.TASKS_AVAILABLE`.

All `Tasks` should inherit from `GenericTask`, which can be imported using:

```python
from foundations import GenericTask

class YourOwnTask(GenericTask):
    'Write your code here'
```

Each task must implement `newTaskRunner`, returning an instance that inherits from `TaskRunner`. This method is called after the server finishes handshaking with the client and understands which task the client wishes to run.

All instances of `TaskRunner` will receive the same instance of `Task` when they initialise. It is hence useful to store states (such as the client's results) here.

### `TaskRunner`

A `TaskRunner` is responsible for handling the tested-program's `stdout` and `stdin`, by sending commands to the client using the `Connection` class.

Please check out the source code located at foundations/tasks/ for more information.

## Example

To quickly implement a simple task, we can utilise the `SimpleTask` class and `SimpleTaskRunner` class.

```python
from foundations import SimpleTask, SimpleTaskRunner
import random


class SampleTaskRunner(SimpleTaskRunner):
    def _run(self, nextInputId, nextInput):
        # Sends this to stdin of the tested-program
        self.stdin(nextInput)
        # Closes stdin causing EOF. This is equivalent to pressing Ctrl+D.
        self.eof()


class SampleTask(SimpleTask):
    def __init__(self):
        # We're telling SimpleTask that we will be using the SampleTaskRunner as our runners.
        super().__init__(SampleTaskRunner)

    def _generateNewInput(self):
        # Generate some inputs when the server runs out of them.
        i = []
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
        # Return that input.
        return ' '.join(i)

```

## Security & Academic Integrity

- No user's source code is accessed in any way

- No compiled binary is uploaded to the server

- No user code is executed on the server

- No server-provided (remote) code is executed on the user's machine - it only pumps to the stdin using pipes and the pipe breaks whenever your program exits.

- The only thing that is uploaded to the server is the console output (from the program being tested)

## Contributing to the project

PR's are welcome!

### Adding a task to the project

If you wish to add a task and make it accessible by everybody, you can do so by opening a PR.

## License

This program is licensed under the [Apache License 2.0
](https://github.com/yyjlincoln/cloud-autotest/blob/master/LICENSE).

Copyright ©️ 2022-present @yyjlincoln
