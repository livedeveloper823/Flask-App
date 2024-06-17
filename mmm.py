from flask import Flask
from threading import Thread
from waitress import serve

app = Flask("__name__")


# @app.route("/")
# def get_bet():
#     # I'm assuming `bet_details` is defined somewhere in your code
#     return bet_details

from flask import Flask
from waitress import serve

app = Flask(__name__)

# @app.route("/dashboard")
# def dashboard():
#     # Your existing function code
#     # ...



@app.route("/dashboard")
def dashboard():
    html_table = """
    <html>
        <head>
            <title>Dashboard</title>
        </head>
        <body>
            <h1>Dashboard</h1>
            <table border="1">
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>1</td>
                    <td>Item 1</td>
                    <td>100</td>
                </tr>
                <tr>
                    <td>2</td>
                    <td>Item 2</td>
                    <td>200</td>
                </tr>
            </table>
        </body>
    </html>
    """
    return html_table


# Start the server in a separate thread
# Thread(
#     target=serve, kwargs={"app": app, "host": "0.0.0.0", "port": 9876}, daemon=True
# ).start()


# Directly serving the app with Waitress on a specified port
if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=5000)

# Note: Since `app.run()` is not being called directly,
# make sure to either run the Flask app programmatically as shown above
# or by setting the FLASK_APP environment variable and using `flask run`
