from flask import Flask, request, jsonify
from gtfs import get_gtfs_feed_static, get_gtfs_rt_my_stop_updates
import json

FLASK_SERVER_IP = '192.168.86.42'
FLASK_SERVER_PORT = 4999

app = Flask(__name__)

@app.route('/api', methods=['GET'])
def my_api():
    # Retrieve the query parameters from the request
    route_id = request.args.get('route_id')
    stop_id = request.args.get('stop_id')

    # Validate the query parameters
    if not route_id or not stop_id:
        return jsonify(error='Missing query parameters'), 400

    print(route_id)
    
    # Process the query parameters
    # TODO: Implement your logic here
    get_gtfs_feed_static()
    output_json = get_gtfs_rt_my_stop_updates(route_id, stop_id)
    return jsonify(output_json)

if __name__ == '__main__':
    app.run(FLASK_SERVER_IP, port=FLASK_SERVER_PORT)

#192.168.86.41:4999/api?route_id=100252&stop_id=6190