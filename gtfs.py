from google.transit import gtfs_realtime_pb2
import requests, zipfile, io
import datetime, csv
import json

gl_list_of_routes = []

def unix_timestamp_to_relative_time(timestamp):
	# Convert Unix timestamp to datetime object
	dt = datetime.datetime.fromtimestamp(timestamp)

	# Calculate the time difference relative to the current moment
	current_time = datetime.datetime.now()
	time_difference = current_time - dt

	# Determine the number of minutes
	minutes = int(time_difference.total_seconds() / 60)

	if minutes < 0:
		if minutes == -1:
			return f"in {abs(minutes)} minute"
		else:
			return f"in {abs(minutes)} minutes"
	elif minutes == 0:
		return "just now"
	else:
		if minutes == 1:
			return f"{minutes} minute ago"
		else:
			return f"{minutes} minutes ago"

def unix_to_rel_min(timestamp):
	# Convert Unix timestamp to datetime object
	dt = datetime.datetime.fromtimestamp(timestamp)

	# Calculate the time difference relative to the current moment
	current_time = datetime.datetime.now()
	time_difference = current_time - dt

	# Determine the number of minutes
	minutes = int(time_difference.total_seconds() / 60)
	return minutes

class Route:
	def __init__(self, route_id, agency_id, route_short_name, route_desc, route_url):
		self.route_id = route_id
		self.agency_id = agency_id
		self.route_short_name = route_short_name
		self.route_desc = route_desc
		self.route_url = route_url
		
class Vehicle:
	def __init__(self, trip_id, direction_id, route_id, start_date, vehicle_id, vehicle_position, timestamp, current_stop_sequence):
		self.trip_id = trip_id
		self.direction_id = direction_id
		self.route_id = route_id
		self.start_date = start_date
		self.vehicle_id = vehicle_id
		self.vehicle_position = vehicle_position
		self.timestamp = timestamp
		self.current_stop_sequence = current_stop_sequence

class Trip:
	def __init__(self, trip_id, direction_id, route_id, start_date, schedule_relationship):
		self.trip_id = trip_id
		self.direction_id = direction_id
		self.route_id = route_id
		self.start_date = start_date
		self.schedule_relationship = schedule_relationship

class Stop:
	def __init__(self, trip_id, arrival_time, stop_id, stop_sequence, shape_dist_traveled, stop_name, stop_position):
		self.trip_id = trip_id
		self.arrival_time = arrival_time
		self.stop_id = stop_id
		self.stop_sequence = stop_sequence
		self.shape_dist_traveled = shape_dist_traveled
		self.stop_name = stop_name
		self.stop_position = stop_position

def get_gtfs_feed_static():
	r = requests.get('https://metro.kingcounty.gov/GTFS/google_transit.zip')
	# check if resp is ok
	z = zipfile.ZipFile(io.BytesIO(r.content))
	z.extractall("gtfs-feed-king-county")
	get_routes_from_gtfs_feed('gtfs-feed-king-county/routes.txt')


def get_route_id_of_route_name(route_name):
	if isinstance(route_name, int):
		route_name = str(route_name)
	
	for r in gl_list_of_routes:
		if route_name.lower() == r.route_short_name.lower():
			return r.route_id
	return None

		
def get_gtfs_rt_my_stop_updates(route_id, stop_id):
	feed = gtfs_realtime_pb2.FeedMessage()
	trip_updates_response = requests.get('https://s3.amazonaws.com/kcm-alerts-realtime-prod/tripupdates.pb', allow_redirects=True)
	feed.ParseFromString(trip_updates_response.content)
	# print(feed)
	# print(feed.entity)
	print("Getting stop updates for route: {} and stop: {}".format(route_id, stop_id))
	output_json = {
		'transit_updates': []
	}
	out_arr = []
	for entity in feed.entity:
		if entity.trip_update.trip.route_id == route_id:
			for stop in entity.trip_update.stop_time_update:
				update_json = {}
				if stop.stop_id == stop_id:
					print("Found a trip! ID: {} || This stop sequence of this stop is {}".format(entity.trip_update.trip.trip_id, stop.stop_sequence))
					update_json['trip_id'] = entity.trip_update.trip.trip_id
					
					curr_timestamp = stop.arrival.time
					delay = stop.arrival.delay
					relative_time = unix_timestamp_to_relative_time(curr_timestamp)
					rel_time_delay = unix_timestamp_to_relative_time(curr_timestamp + delay)
					print("Time: {} || With current delays: {}".format(relative_time, rel_time_delay))
					
					out_arr.append(curr_timestamp + delay)

					update_json['time'] = relative_time
					update_json['time_w_delay'] = rel_time_delay
					output_json['transit_updates'].append(update_json)
	
	out_arr.sort()
	new_out = []
	for unix_time in out_arr:
		if abs(unix_to_rel_min(unix_time)) <= 90:
			new_out.append(unix_time)
	out_arr = new_out

	result = ""
	if len(out_arr) == 0:
		result += "I don't see any buses. Check again later."
	elif len(out_arr) == 1:
		result += "I only see one bus."
	else:
		result += "I see {} buses! ".format(len(out_arr))
	
	for i, unix_time in enumerate(out_arr):
		if i == 0:
			if len(out_arr) <= 1:
				result += "It "
			else: 
				result += "The first "
		
			if unix_to_rel_min(unix_time) > 0:
				result += "came "
			else:
				result += "comes "
		elif i == len(out_arr) - 1:
			result += "and the last one I see comes "
		else:
			result += "the one after comes "
		
		friendly = unix_timestamp_to_relative_time(unix_time)
		result += f"{friendly}, "
	result = result.rstrip('"')
	result += "."

	output_json['message'] = result
	
	return output_json






# def get_gtfs_rt_trips_from_route(route_id):
#   list_of_trips = []
#   feed = gtfs_realtime_pb2.FeedMessage()
#   trip_updates_response = requests.get('https://s3.amazonaws.com/kcm-alerts-realtime-prod/tripupdates.pb', allow_redirects=True)
#   feed.ParseFromString(trip_updates_response.content)
#   for entity in feed.entity:
#     if entity.trip_update.trip.route_id == route_id:
#       #print(entity)
#       trip_id = entity.trip_update.trip.trip_id
#       direction_id = entity.trip_update.trip.direction_id
#       start_date = entity.trip_update.trip.start_date
#       schedule_relationship = entity.trip_update.trip.schedule_relationship
#       my_trip = Trip(trip_id, direction_id, route_id, start_date, schedule_relationship)
#       list_of_trips.append(my_trip)
#   return list_of_trips
					
# def get_gtfs_rt_vehicles(route_id, stop_id):
#   feed = gtfs_realtime_pb2.FeedMessage()
#   vehicle_pos_response = requests.get('https://s3.amazonaws.com/kcm-alerts-realtime-prod/vehiclepositions.pb', allow_redirects=True)
#   feed.ParseFromString(vehicle_pos_response.content)
#   list_of_vehicles = []
#   for entity in feed.entity:
#     if entity.vehicle.trip.route_id == route_id:
#       trip_id = entity.vehicle.trip.trip_id
#       direction_id = entity.vehicle.trip.direction_id
#       # route_id = entity.vehicle.trip.route_id
#       start_date = entity.vehicle.trip.start_date
#       vehicle_id = entity.vehicle.vehicle.id
#       position = (entity.vehicle.position.latitude, entity.vehicle.position.longitude)
#       timestamp = entity.vehicle.timestamp
#       current_stop_sequence = entity.vehicle.current_stop_sequence
			
#       # only display the vehicles that will hit my stop
#       my_stops = get_stops_from_trip(trip_id)
#       vehicle_passes_my_stop = False
#       for stop in my_stops:
#         if stop.stop_id == stop_id:
#           vehicle_passes_my_stop = True
#       if not vehicle_passes_my_stop:
#         continue
			
#       vehicle_had_gone = False
#       for stop in my_stops:
#         if stop.stop_id == stop_id and float(stop.stop_sequence) >= current_stop_sequence:
#           vehicle_had_gone = True
#       if not vehicle_had_gone:
#         continue
			
#       my_vehicle = Vehicle(trip_id, direction_id, route_id, start_date, vehicle_id, position, timestamp, current_stop_sequence)
#       list_of_vehicles.append(my_vehicle)
#   return list_of_vehicles

def get_routes_from_gtfs_feed(routes_file_path):
  with open(routes_file_path, 'r') as file:
    for line_number, line in enumerate(file):
      if line_number == 0:
        continue  # Skip the first line
      current_line = line.split(",")
      current_route = Route(current_line[0], current_line[1], current_line[2].strip('"'), current_line[4], current_line[6])
      gl_list_of_routes.append(current_route)
      # print("ID: {}, Name: {}, Desc: {}, URL: {}".format(current_route.route_id, current_route.route_short_name, current_route.route_desc, current_route.route_url))

def get_directions_from_route_id(route_id):
	trips_file = 'gtfs-feed-king-county/trips.txt'
	with open(trips_file, 'r', encoding='utf-8-sig') as trips_csv:
		trips_reader = csv.DictReader(trips_csv)
		directions = {}

		for trip in trips_reader:
			if trip['route_id'] == route_id:
				direction_id = trip['direction_id']
				headsign = trip['trip_headsign']

				if direction_id not in directions:
					directions[direction_id] = headsign

				if len(directions) == 2:
					break
	return directions

def get_trip_ids_from_route_direction(route_id, direction_id):
	if isinstance(direction_id, int):
		direction_id = str(direction_id)
	trips_file = 'gtfs-feed-king-county/trips.txt'
	with open(trips_file, 'r', encoding='utf-8-sig') as trips_csv:
		trips_reader = csv.DictReader(trips_csv)
		list_of_trips = []

		for t in trips_reader:
			if t['route_id'] == route_id and t['direction_id'] == direction_id:
				list_of_trips.append(t['trip_id'])
				return list_of_trips # Returns the first trip found
	return list_of_trips

def get_stops_from_trip(trip_id):
	if isinstance(trip_id, int):
		trip_id = str(trip_id)
	
	stops = []
	stop_times_file = 'gtfs-feed-king-county/stop_times.txt'
	with open(stop_times_file, 'r', encoding='utf-8-sig') as stop_times_csv:
		stop_times_reader = csv.DictReader(stop_times_csv)
		for stop_time in stop_times_reader:
			if stop_time['trip_id'] == trip_id:
				stop_id = stop_time['stop_id']
				stop = get_stop_name_position_from_id(stop_id)
				stops.append(stop)
	return stops

def get_stop_name_position_from_id(stop_id):
	stops_path = 'gtfs-feed-king-county/stops.txt'
	with open(stops_path, 'r') as file:
		for line_number, line in enumerate(file):
			if line_number == 0:
				continue  # Skip the first line
			current_line = line.split(",")
			if current_line[0] == stop_id:
				stop_name = current_line[2]
				stop_position = (float(current_line[4]), float(current_line[5]))
				stop = {'stop_id': stop_id, 'stop_name': stop_name, 'stop_pos_lat': float(current_line[4]), 'stop_pos_lon': float(current_line[5])}
				return stop
	return None

# MAIN CODE HERE  
#get_gtfs_feed_static()
#route_name = input("What's the route?  ")
#my_route_id = get_route_id_of_route_name(route_name)
#directions = get_directions_from_route_id(my_route_id)
#print("Select the direction")
#for direction_id, headsign in directions.items():
#    print(f"Direction ID: {direction_id}, Headsign: {headsign}")
#my_dir_id = input("What's the direction ID?  ")    
#my_trips = get_trip_ids_from_route_direction(my_route_id, my_dir_id)
#my_stops = get_stops_from_trip(my_trips[0])
#for stop in my_stops:
#	print(f"Stop ID: {stop['stop_id']}, Stop Name: {stop['stop_name']}, Latitude: {stop['stop_pos_lat']}, Longitude: {stop['stop_pos_lon']}")
#my_stop_id = input("What's the stop ID of your stop?  ")
#print(f"Looking for route_id: {my_route_id} and stop_id: {my_stop_id}")
#get_gtfs_rt_my_stop_updates(my_route_id, my_stop_id)
