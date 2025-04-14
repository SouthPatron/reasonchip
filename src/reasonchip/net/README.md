# Networking

The networking layer provides code for:

- Workers: runners of pipelines;
- Client: the python-native client code which request the execution of a pipeline;
- Broker: the coordinator between clients and workers;

And the transports over which packets are shipped are all within the
`transports` directory.


## Filesystem layout

| Location | Description |
| ------------------------- | ----------------------------------------------- |
| [broker](./broker/) | Broker code |
| [client](./client/) | Client code |
| [transports](./transports/) | Transport layer with different transports |
| [worker](./worker/) | Worker code |


