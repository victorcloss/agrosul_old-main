from flask import Flask
from dash import Dash, html

# Create the Flask server instance
app = Flask(__name__)

# Create the Dash app using the Flask server instance
dash_app = Dash(__name__, server=app, url_base_pathname='/')

# Define the layout for the Dash app
dash_app.layout = html.Div([
    html.H1("Hello from Dash!", style={'color': 'blue'}),
    html.P("This is a Dash layout running on top of Flask.")
])

# Define a basic route for Flask
@app.route("/")
def hello():
    return redirect("/")

#Optional: Run the server if executed directly (useful for debugging locally)
if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8050)
