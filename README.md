# SuperMon

Supervisord monitor

Web application to monitor and control [supervisord](http://supervisord.org/) servers

## Installation

Clone the repository:

```
git clone https://github.com/jsch/SuperMon.git
```

Then set the working directory to the application:

```
cd SuperMon
```

The application requires Python 3.5 or latter and the following modules:

-  [gevent](https://pypi.org/project/gevent/)
-  [greenlet](https://pypi.org/project/greenlet/)
-  [Pykka](https://pypi.org/project/Pykka/)
-  [pyzmq](https://pypi.org/project/pyzmq/)
-  [zmq](https://pypi.org/project/zmq/)

These modules can be installed with:

```
pip install -r requirements.txt
```

## Configuration

The application needs to be configured indicating the servers where
`supervisord` is running.

This is done by copying/moving the `config.py.dist` file to
`config.py`.

With a text editor add the servers that are going to be monitored.

This file contains the list of `SUPERVISORS`, where each element
is a directory with the definition of one supervisor.

The list looks like this:

```
SUPERVISORS = [
    {
        'server_name': 'localhost',
        'ip_address': '127.0.0.1',
        'port': 9001
     },
]
```

## Running the application

Once the application is configured it can be started with:

```
python supermon.py
```

and is available at:

```
http://localhost:8080
```

There are some command line arguments to modify how the application
works, but I leave this for you to discover with:

```
python supermon.py -h
```
