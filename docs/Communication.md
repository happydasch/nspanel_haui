# Communication Overview

- [Communication Overview](#communication-overview)
  - [Overview](#overview)
    - [Client](#client)
    - [Server](#server)
    - [Talking together](#talking-together)
  - [Basic connection handling](#basic-connection-handling)
  - [Client Connection State (ESPHome Component)](#client-connection-state-esphome-component)
  - [Server Connection State (AppDaemon Component)](#server-connection-state-appdaemon-component)

## Overview

### Client

- Nextion Display
- ESPHome Device

### Server

- AppDaemon App

### Talking together

```text
Client (Display <-> Device) <-> Server (App)

                UART        MQTT
```

The device talks to the display via UART the device talks also to the server via MQTT.

The client needs to establish a connection with the server in order to be able to do anything.

## Basic connection handling

When the client is connected to the server the connection is being kept alive by the process described below:

- The client publishes a heartbeat message to mqtt.
- The server sees the heartbeat message and sends a heartbeat message back to the client by mqtt.
- The client receives the heartbeat message and confirms that the connection is still active.
- If the client does not receive a heartbeat message within a certain time period, it assumes the connection is lost and tries to reconnect.
- If the server does not receive a heartbeat message within a certain time period, it assumes the connection is lost and closes the connection.

## Client Connection State ([ESPHome Component](ESPHome.md))

When the client is not connected, it will try to connect.
The process is as described below:

1. Initialize client state to "DISCONNECTED".
2. Send a connection request to the server.
3. Wait for a connection response from the server.
4. Send a confirmation message to the server.
5. Wait for a connection initialization response from the server.
6. If connection is initialized, set client state to "CONNECTED" and start sending heartbeat messages to the server.
7. If heartbeat messages are not received from the server within a certain time frame, assume the connection is lost and attempt to reconnect.

## Server Connection State ([AppDaemon Component](AppDaemon.md))

On the server side, just handle connection requests.
The process is as described below:

1. Initialize server state to "DISCONNECTED".
2. Wait for a connection request from the client.
3. Send a connection confirmation to the client.
4. If connection is confirmed, set server state to "CONNECTED" and start receiving heartbeat messages from the client.
5. If heartbeat messages are not received from the client within a certain time frame, assume the connection is lost and terminate the connection.
6. If heartbeat messaged are received from the client but the client is not connecten then send a message to disconnect.
