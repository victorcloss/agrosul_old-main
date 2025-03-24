from dash import Dash, dcc, html, Input, Output, State, dash_table
import pandas as pd
import dash_bootstrap_components as dbc

# Sample initial data
initial_data = {
    "Grandeza": ['Peso Frango (kg)', 'Peso Pata (kg)', 'Valor Frango (R$)', 'Valor Pata A (US$)', 'Valor Pata B (US$)', 'Valor Pata C/queda (US$)', 'Cotação (R$/US$)'], 
    "Valores":   [                 3,             0.05,                  4.20,               3.8,                   3.5,                       -3.6,               5.76],
}
df = pd.DataFrame(initial_data)

app = Dash(__name__)

app.layout = html.Div([
    # Add CSS to hide the column headers
    dbc.Card([
    dash_table.DataTable(
        id='parametros-table',
        columns=[
            {"name": "Grandeza", "id": "Grandeza", "type": "text"},
            {"name": "Valores", "id": "Valores", "editable": True, "type": "numeric"},
            ],
        data=df.to_dict('records'),
    ),
    ]),
    html.Button("Convert to DataFrame", id="convert-btn", n_clicks=0),
    html.Div(id='output-div')  # Optional: for debugging purposes
])


@app.callback(
    Output('output-div', 'children'),
    Input('convert-btn', 'n_clicks'),
    State('parametros-table', 'data')
)
def convert_to_dataframe(n_clicks, table_data):
    if n_clicks > 0:
        # Convert table data (list of dicts) to DataFrame
        df = pd.DataFrame(table_data)
        # Display the DataFrame as a string (or you could use it further)
        return html.Pre(f"DataFrame:\n{df}")
    return "Click the button to convert table data to DataFrame."

if __name__ == '__main__':
    app.run_server(debug=True)
