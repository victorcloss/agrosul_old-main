import dash
import dash_bootstrap_components as dbc
from dash import html, dcc

# Initialize the app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Layout
app.layout = dbc.Container([
    dbc.Card(
        [
            dbc.CardHeader("Export Card Example"),
            dbc.CardBody(
                [
                    html.H5("This is the card content.", className="card-title"),
                    dcc.Graph(
                        id='example-plot',
                        figure={
                            'data': [
                                {'x': [1, 2, 3], 'y': [4, 1, 2], 'type': 'bar', 'name': 'SF'},
                                {'x': [1, 2, 3], 'y': [2, 4, 5], 'type': 'bar', 'name': 'NYC'}
                            ],
                            'layout': {
                                'title': 'Simple Bar Plot'
                            }
                        }
                    )
                ]
            )
        ],
        id='resultado-card'
    ),
    html.Br(),
    dbc.Button("Export to PDF", id="export-button", color="primary", className="mb-2"),

    # Add html2canvas and jsPDF libraries to the layout
    html.Script(src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/0.4.1/html2canvas.min.js"),
    html.Script(src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/1.3.2/jspdf.min.js"),

    # JavaScript to handle the PDF export
    html.Script('''
        document.getElementById('export-button').addEventListener('click', function() {
            var element = document.getElementById('resultado-card');
            html2canvas(element).then(function(canvas) {
                var imgData = canvas.toDataURL('image/png');
                var pdf = new jsPDF();
                pdf.addImage(imgData, 'PNG', 10, 10);
                pdf.save('card_content.pdf');
            });
        });
    ''')
])

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True)
