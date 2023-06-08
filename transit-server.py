from flask import Flask, request, jsonify, render_template, redirect, url_for
from gtfs import (
    get_gtfs_feed_static,
    get_gtfs_rt_my_stop_updates,
    get_route_id_of_route_name,
)
from flask_cors import CORS
from init_db import get_db_connection
import json

FLASK_SERVER_IP = "192.168.86.42"
FLASK_SERVER_PORT = 4999

app = Flask(__name__)
CORS(app)


@app.before_first_request
def setup():
    get_gtfs_feed_static()
    print("Retrieved GTFS static from King County Metro")
    # print("Retrieved GTFS static from SoundTransit Open Transit Data")


@app.route("/api", methods=["GET"])
def my_api():
    route_id = request.args.get("route_id")
    stop_id = request.args.get("stop_id")
    print("Looking for route_id={} and stop_id={}".format(route_id, stop_id))

    # Validate the query parameters
    if not route_id or not stop_id:
        return jsonify(error="Missing query parameters"), 400

    output_json = get_gtfs_rt_my_stop_updates(route_id, stop_id)
    return jsonify(output_json)


@app.route("/convert", methods=["GET"])
def convert_to_route_id():
    route_name = request.args.get("route_name")

    converted_id = get_route_id_of_route_name(route_name)

    if not route_name:
        return jsonify(error="Missing query parameters"), 400

    if converted_id is None:
        return jsonify(error="Cannot find route"), 400

    return {"route_id": converted_id}


@app.route("/")
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users;")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("index.html", users=users)


@app.route("/create_user", methods=["GET", "POST"])
def create_user_form():
    if request.method == "POST":
        my_name = request.form["name"]
        my_email = request.form["email"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (name, email)" "VALUES (%s, %s)", (my_name, my_email)
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("index"))
    return render_template("create.html")


# DELETE operation - Delete the specified user
@app.route("/delete", methods=["POST"])
def delete():
    id = request.form["id"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM users WHERE id=%s", (id))

    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("index"))


# CREATE user JSON
@app.route("/api/user", methods=["POST"])
def create_user():
    content_type = request.headers.get("Content-Type")
    if content_type != "application/json":
        return "Content type is not supported"

    # handle json payload
    if content_type == "application/json":
        data = request.get_json()
        my_name = data["name"]
        my_email = data["email"]

        conn = get_db_connection()
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id;",
                    (my_name, my_email),
                )
                user_id = cursor.fetchone()[0]
        return {
            "message": f"User {my_name} created with {my_email}.",
            "id": user_id,
            "name": my_name,
            "email": my_email,
        }, 201

    return


# GET all users
@app.route("/api/user", methods=["GET"])
def get_all_users():
    conn = get_db_connection()
    with conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users;")
            users = cursor.fetchall()
            if users:
                result = []
                for user in users:
                    # Retrieve the routes for the specified user ID
                    get_routes_query = """
                        SELECT route_num, stop_num
                        FROM routes
                        WHERE user_id = %s;
                    """
                    cursor.execute(get_routes_query, (user[0],))
                    my_routes = cursor.fetchall()

                    # Create a list of dictionaries to hold the routes data
                    routes_data = []
                    for route in my_routes:
                        this_route = {"route_num": route[0], "stop_num": route[1]}
                        routes_data.append(this_route)

                    result.append(
                        {
                            "id": user[0],
                            "name": user[1],
                            "email": user[2],
                            "routes": routes_data,
                        }
                    )
                return jsonify(result)
            else:
                return jsonify({"error": f"Users not found."}), 404


# GET a user
@app.route("/api/user/<int:user_id>", methods=["GET"])
def get_user(user_id):
    conn = get_db_connection()
    with conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()

            # Retrieve the routes for the specified user ID
            get_routes_query = """
                SELECT route_num, stop_num
                FROM routes
                WHERE user_id = %s;
            """
            cursor.execute(get_routes_query, (user_id,))
            my_routes = cursor.fetchall()

            # Create a list of dictionaries to hold the routes data
            routes_data = []
            for route in my_routes:
                this_route = {"route_num": route[0], "stop_num": route[1]}
                routes_data.append(this_route)

            if user:
                return jsonify(
                    {
                        "id": user[0],
                        "name": user[1],
                        "email": user[2],
                        "routes": routes_data,
                    }
                )
            else:
                return jsonify({"error": f"User with ID {user_id} not found."}), 404


# UPDATE a user
@app.route("/api/user/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    conn = get_db_connection()
    data = request.get_json()
    my_name = data["name"]
    my_email = data["email"]
    update_query = """
        UPDATE users
        SET name = %s, email = %s
        WHERE id = %s;
    """
    with conn:
        with conn.cursor() as cursor:
            cursor.execute(update_query, (my_name, my_email, user_id))
            if cursor.rowcount == 0:
                return jsonify({"error": f"User with ID {user_id} not found."}), 404
    return jsonify(
        {
            "id": user_id,
            "name": my_name,
            "message": f"User with ID {user_id} updated.",
            "email": my_email,
        }
    )


# DELETE a user
@app.route("/api/user/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    conn = get_db_connection()
    delete_query = """
        DELETE FROM users
        WHERE id = %s;
    """
    with conn:
        with conn.cursor() as cursor:
            cursor.execute(delete_query, (user_id,))
            if cursor.rowcount == 0:
                return jsonify({"error": f"User with ID {user_id} not found."}), 404
    return jsonify({"message": f"User with ID {user_id} deleted."})


# CREATE route JSON
@app.route("/api/route", methods=["POST"])
def create_route():
    content_type = request.headers.get("Content-Type")
    if content_type != "application/json":
        return "Content type is not supported"

    # handle json payload
    if content_type == "application/json":
        data = request.get_json()
        my_route_id = data["route_num"]
        my_stop_id = data["stop_num"]
        my_user_id = data["user_id"]

        conn = get_db_connection()
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO routes (route_num, stop_num, user_id) VALUES (%s, %s, %s) RETURNING id;",
                    (my_route_id, my_stop_id, my_user_id),
                )
                my_id = cursor.fetchone()[0]
        return {
            "message": f"Route number {my_route_id} with stop {my_stop_id} created for user {my_user_id}. This record has ID {my_id}"
        }, 201

    return


# DELETE a route
@app.route("/api/route/<int:id>", methods=["DELETE"])
def delete_route(id):
    conn = get_db_connection()
    delete_query = """
        DELETE FROM routes
        WHERE id = %s;
    """
    with conn:
        with conn.cursor() as cursor:
            cursor.execute(delete_query, (id,))
            if cursor.rowcount == 0:
                return jsonify({"error": f"Route with ID {id} not found."}), 404
    return jsonify({"message": f"Route with ID {id} deleted."})


# GET all routes
@app.route("/api/route", methods=["GET"])
def get_all_routes():
    conn = get_db_connection()
    with conn:
        with conn.cursor() as cursor:
            query = """
                SELECT routes.id, routes.route_num, routes.stop_num, users.name, users.email
                FROM routes
                JOIN users ON routes.user_id = users.id
            """
            cursor.execute(query)
            routes = cursor.fetchall()
            if routes:
                routes_data = []
                for r in routes:
                    this_route = {
                        "id": r[0],
                        "route_num": r[1],
                        "stop_num": r[2],
                        "user_name": r[3],
                        "user_email": r[4],
                    }
                    routes_data.append(this_route)
                return jsonify({"routes": routes_data})
            else:
                return jsonify({"error": f"Routes not found."}), 404


if __name__ == "__main__":
    app.run()


# if __name__ == '__main__':
#    app.run(FLASK_SERVER_IP, port=FLASK_SERVER_PORT)

# 192.168.86.41:4999/api?route_id=100252&stop_id=6190
