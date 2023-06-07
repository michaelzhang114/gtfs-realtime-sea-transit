import psycopg2
import os

def get_db_connection():
    conn = psycopg2.connect(os.environ.get("DB_EXT_STRING"))
    #conn = psycopg2.connect(os.environ.get("DB_INT_STRING"))
    return conn

conn = get_db_connection()
cursor = conn.cursor()

# create a new table
cursor.execute('DROP TABLE IF EXISTS users CASCADE;')
cursor.execute("CREATE TABLE users (id SERIAL PRIMARY KEY, name VARCHAR(255) NOT NULL, email VARCHAR(255) NOT NULL)")
cursor.execute('DROP TABLE IF EXISTS routes;')
cursor.execute("CREATE TABLE routes (id SERIAL PRIMARY KEY, route_num INTEGER NOT NULL, stop_num INTEGER NOT NULL, user_id INTEGER REFERENCES users (id) ON DELETE CASCADE);")


# populate with 3 users
cursor.execute("INSERT INTO users (name, email) VALUES ('John Doe', 'john@example.com')")
cursor.execute("INSERT INTO users (name, email) VALUES ('Mary Beck', 'mary@hello.com')")
cursor.execute("INSERT INTO users (name, email) VALUES ('Jane Smith', 'jane@example.com')")

# define the routes for each user
users_routes = {
    1: [
        {"route_num": 100275, "stop_num": 2255},
    ],
    2: [
        {"route_num": 100340, "stop_num": 26665},
    ],
    3: [
        {"route_num": 100252, "stop_num": 6220},
        {"route_num": 100340, "stop_num": 26690}
    ]
}

for user_id, routes in users_routes.items():
    for route in routes:
        route_num = route["route_num"]
        stop_num = route["stop_num"]
        cursor.execute("INSERT INTO routes (route_num, stop_num, user_id) VALUES (%s, %s, %s)",
                    (route_num, stop_num, user_id))


conn.commit()

cursor.close()
conn.close()