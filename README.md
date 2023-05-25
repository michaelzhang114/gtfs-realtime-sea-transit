# gtfs-realtime-sea-transit

## Usage
The gunicorn/Flask server hosts the REST API endpoint: 
```
http://FLASK_SERVER_IP:FLASK_SERVER_PORT/api?route_id=<ID of your route>&stop_id=<ID of your stop>
```

## transit-server.py

Modify `FLASK_SERVER_IP` and `FLASK_SERVER_PORT` for your environment. This is where the Flask server will run. In my setup, IP == the LAN address of my RPI.

## Keep Flask Server running using Gunicorn

1. **Install Gunicorn:**

    ```
    sudo apt-get update
    sudo apt-get install gunicorn
    ```

2. **Create a Gunicorn configuration file:**

    - Create a new file, e.g., `gunicorn_config.py`, to define the Gunicorn settings.
    - Customize the configuration based on your requirements. For example:

    ```python
    bind = '0.0.0.0:8000'  # Replace with the desired host and port
    workers = 4  # Number of worker processes
    threads = 2  # Number of worker threads per process
    ```

3. **Start Gunicorn server and test your API**

    ```
    gunicorn -c gunicorn_config.py transit-server.py:app
    ```

4. **Keep server running**
    - By default, Gunicorn will run continuously until you stop it manually.
    - If you're running the server on a remote machine or a cloud server, you can use tools like nohup or screen to keep the process running even after you close the terminal session. For example:

    ```
    nohup gunicorn -c gunicorn_config.py transit-server:app &
    ```

5. **Terminate Gunicorn process**
```
pkill gunicorn
```
