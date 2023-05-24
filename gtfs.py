from google.transit import gtfs_realtime_pb2
import requests, zipfile, io
import datetime

def unix_timestamp_to_relative_time(timestamp):
    # Convert Unix timestamp to datetime object
    dt = datetime.datetime.fromtimestamp(timestamp)

    # Calculate the time difference relative to the current moment
    current_time = datetime.datetime.now()
    time_difference = current_time - dt

    # Determine the number of minutes
    minutes = int(time_difference.total_seconds() / 60)

    if minutes < 0:
        return f"in {abs(minutes)} minutes"
    elif minutes == 0:
        return "just now"
    else:
        return f"{minutes} minutes ago"

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
    
def get_gtfs_rt_my_stop_updates(route_id, stop_id):
  feed = gtfs_realtime_pb2.FeedMessage()
  trip_updates_response = requests.get('https://s3.amazonaws.com/kcm-alerts-realtime-prod/tripupdates.pb', allow_redirects=True)
  feed.ParseFromString(trip_updates_response.content)
  # print(feed)
  # print(feed.entity)
  print("Getting stop updates for route: {} and stop: {}".format(route_id, stop_id))

  for entity in feed.entity:
    if entity.trip_update.trip.route_id == route_id:
      for stop in entity.trip_update.stop_time_update:
        if stop.stop_id == stop_id:
          print("Found a trip! ID: {} || This stop sequence of this stop is {}".format(entity.trip_update.trip.trip_id, stop.stop_sequence))
          curr_timestamp = stop.arrival.time
          delay = stop.arrival.delay
          relative_time = unix_timestamp_to_relative_time(curr_timestamp)
          rel_time_delay = unix_timestamp_to_relative_time(curr_timestamp + delay)
          print("Time: {} || With current delays: {}".format(relative_time, rel_time_delay))
  
def get_gtfs_rt_trips_from_route(route_id):
  list_of_trips = []
  feed = gtfs_realtime_pb2.FeedMessage()
  trip_updates_response = requests.get('https://s3.amazonaws.com/kcm-alerts-realtime-prod/tripupdates.pb', allow_redirects=True)
  feed.ParseFromString(trip_updates_response.content)
  for entity in feed.entity:
    if entity.trip_update.trip.route_id == route_id:
      #print(entity)
      trip_id = entity.trip_update.trip.trip_id
      direction_id = entity.trip_update.trip.direction_id
      start_date = entity.trip_update.trip.start_date
      schedule_relationship = entity.trip_update.trip.schedule_relationship
      my_trip = Trip(trip_id, direction_id, route_id, start_date, schedule_relationship)
      list_of_trips.append(my_trip)
  return list_of_trips
          
def get_gtfs_rt_vehicles(route_id, stop_id):
  feed = gtfs_realtime_pb2.FeedMessage()
  vehicle_pos_response = requests.get('https://s3.amazonaws.com/kcm-alerts-realtime-prod/vehiclepositions.pb', allow_redirects=True)
  feed.ParseFromString(vehicle_pos_response.content)
  list_of_vehicles = []
  for entity in feed.entity:
    if entity.vehicle.trip.route_id == route_id:
      trip_id = entity.vehicle.trip.trip_id
      direction_id = entity.vehicle.trip.direction_id
      # route_id = entity.vehicle.trip.route_id
      start_date = entity.vehicle.trip.start_date
      vehicle_id = entity.vehicle.vehicle.id
      position = (entity.vehicle.position.latitude, entity.vehicle.position.longitude)
      timestamp = entity.vehicle.timestamp
      current_stop_sequence = entity.vehicle.current_stop_sequence
      
      # only display the vehicles that will hit my stop
      my_stops = get_stops_from_trip(trip_id)
      vehicle_passes_my_stop = False
      for stop in my_stops:
        if stop.stop_id == stop_id:
          vehicle_passes_my_stop = True
      if not vehicle_passes_my_stop:
        continue
      
      vehicle_had_gone = False
      for stop in my_stops:
        if stop.stop_id == stop_id and float(stop.stop_sequence) >= current_stop_sequence:
          vehicle_had_gone = True
      if not vehicle_had_gone:
        continue
      
      

      my_vehicle = Vehicle(trip_id, direction_id, route_id, start_date, vehicle_id, position, timestamp, current_stop_sequence)
      list_of_vehicles.append(my_vehicle)
  return list_of_vehicles

def get_routes_from_gtfs_feed(routes_file_path):
  list_of_routes = []
  with open(routes_file_path, 'r') as file:
    for line_number, line in enumerate(file):
      if line_number == 0:
        continue  # Skip the first line
      current_line = line.split(",")
      current_route = Route(current_line[0], current_line[1], current_line[2], current_line[4], current_line[6])
      list_of_routes.append(current_route)
      # print("ID: {}, Name: {}, Desc: {}, URL: {}".format(current_route.route_id, current_route.route_short_name, current_route.route_desc, current_route.route_url))
  return list_of_routes

def get_stops_from_trip(trip_id):
  stop_times_path = 'gtfs-feed-king-county/stop_times.txt'
  list_of_stops = []
  with open(stop_times_path, 'r') as file:
    for line_number, line in enumerate(file):
      if line_number == 0:
        continue  # Skip the first line
      current_line = line.split(",")
      if current_line[0] == trip_id:
        # print(current_line)
        curr_stop_id = current_line[3]
        stop_n, stop_pos = get_stop_name_position_from_id(curr_stop_id)
        current_stop = Stop(current_line[0], curr_stop_id, current_line[3], current_line[4], current_line[8], stop_n, stop_pos)
        list_of_stops.append(current_stop)
        #print("Trip ID: {}, Stop ID: {}, Stop Seq: {}, Dist: {}, Name: {}, Pos: {}".format(current_stop.trip_id, current_stop.stop_id, current_stop.stop_sequence, current_stop.shape_dist_traveled, current_stop.stop_name, current_stop.stop_position))
  return list_of_stops

def get_stop_name_position_from_id(stop_id):
  stops_path = 'gtfs-feed-king-county/stops.txt'
  list_of_stops = []
  with open(stops_path, 'r') as file:
    for line_number, line in enumerate(file):
      if line_number == 0:
        continue  # Skip the first line
      current_line = line.split(",")
      if current_line[0] == stop_id:
        stop_name = current_line[2]
        stop_position = (float(current_line[4]), float(current_line[5]))
  return (stop_name, stop_position)

# MAIN CODE HERE  

# Get the static gtfs feed, dump into folder
get_gtfs_feed_static()

# list_of_routes = get_routes_from_gtfs_feed('gtfs-feed-king-county/routes.txt')

# Bus 8 Seattle Center
# get_gtfs_rt_my_stop_updates("100275", "2291")
# list_of_vehicles = get_gtfs_rt_vehicles("100275", "2291")
# for v in list_of_vehicles:
#   print(v.__dict__)

# Bus 8 Mount Baker
# get_gtfs_rt_my_stop_updates("100275", "2255")
# list_of_vehicles = get_gtfs_rt_vehicles("100275", "2255")
# for v in list_of_vehicles:
#   print(v.__dict__)

# Bus 62 
get_gtfs_rt_my_stop_updates("100252", "6190")
list_of_vehicles = get_gtfs_rt_vehicles("100252", "6190")
for v in list_of_vehicles:
  print(v.__dict__)


# list_of_stop_of_trip = get_stops_from_trip("599398763")



# for t in list_of_trips:
#   print(t.__dict__)

# bus 8's route ID is 100275; direction ID is 1 towards cap hill
# bus 8 towards cap hill one trip ID: 605082613
# my stop is "Denny Way & Westlake" and the stop ID is 2255 (going to cap hill) & 2291

# bus 62; route 100252; 
# 7th ave & blanchard stop: 6190 & 6220