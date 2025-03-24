from flask import Flask, request, send_file
import os
from dash import dcc, html, Dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import subprocess
from fpdf import FPDF
import base64
from io import BytesIO

# Import the content of each tab from the separate module files
from tabs import dia_tab_v2, financeiro_tab_v2, historico_tab_v2, upload_tab, tab_functions

# careful here, it seems this warning is irrelevant:
# https://stackoverflow.com/questions/71082494/getting-a-warning-when-using-a-pyodbc-connection-object-with-pandas
from warnings import filterwarnings
filterwarnings("ignore", category=UserWarning, message='.*pandas only supports SQLAlchemy connectable.*')



# upload folder
UPLOAD_DIRECTORY = "uploads"
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)


global PF, VF, PP, VA, VB, VC, USS
PF = 3
VF = 4.2
PP = 0.05
VA = 1.05
VB = 0.95
VC = -1.00
USS= 6.3

app = Flask(__name__)
dash_app = Dash(__name__, 
                external_stylesheets=[dbc.themes.FLATLY, '/assets/styles.css'],  
                url_base_pathname='/', 
                server=app, 
                suppress_callback_exceptions=True)



dash_app.title = 'THEIA - Agrosul'
dash_app._favicon = "icon.png"



# Define the RTSP stream URLs to check
rtsp_streams = [
    'rtsp://127.0.0.1:5202/ds-test',
    'rtsp://127.0.0.1:5203/ds-test-2'
]

# Check if both RTSP streams are running before starting new ones
stream_status = tab_functions.are_ffmpeg_streams_running(rtsp_streams)
# Placeholder for the ffmpeg subprocess
ffmpeg_process = None
ffmpeg_process2= None


# Define the layout with tabs
dash_app.layout = dbc.Row([
    dbc.Col([       
        html.Hr(), 
        dbc.Card([
            dbc.Col(html.Img(src=r'assets/logo2.png', className='responsive-img'),
		xs=6, sm=4, md=4, lg=4, xl=10
		),           
            html.Hr(style={'margin':'10px'}),
            html.H5('Parâmetros do Frango:', style={'margin':'10px'}),
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([
                                html.H3(dbc.Badge('Peso Frango', color='secondary', className="me-3")),
                                html.Hr(),
                            dbc.Row([
                                dbc.Col(
                                    html.H5('kg:'),
                                ),
                                dbc.Col(
                                    dcc.Input(id='peso-F', 
                                                    value=PF, 
                                                    style={"width": 50, "height": 30},)
                                ),
                                dbc.Col(),
                                ]),                         
                                ]),  className="m-4"), xl=10),
                dbc.Col(),
            ]), 
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([
                                html.H3(dbc.Badge('Valor Frango', color='success', className="me-3")),
                                html.Hr(),
                            dbc.Row([
                                dbc.Col(
                                    html.H5('R$/kg:'),
                                ),
                                dbc.Col(
                                    dcc.Input(id='valor-F', 
                                                    value=VF, 
                                                    style={"width": 50, "height": 30},)
                                ),
                                dbc.Col(),
                                ]),                         
                                ]),  className="m-4"), xl=10),
                dbc.Col(),
            ]), 
            html.Hr(style={'margin-left':'100px','margin-right':'100px'}),
            html.H5('Parâmetros das Patas:', style={'margin':'10px'}),
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([
                                html.H3(dbc.Badge('Peso Pata', color='secondary', className="me-3")),
                                html.Hr(),
                            dbc.Row([
                                dbc.Col(
                                    html.H5('kg:'),
                                ),
                                dbc.Col(
                                    dcc.Input(id='peso-P', 
                                                    value=PP, 
                                                    style={"width": 50, "height": 30},)
                                ),
                                dbc.Col(),
                                ]),                         
                                ]),  className="m-4"), xl=10),
                dbc.Col(),
            ]), 
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([
                                html.H3(dbc.Badge('Patas A', color='success', className="me-3")),
                                html.Hr(),
                            dbc.Row([
                                dbc.Col(
                                    html.H5('US$/kg:'),
                                ),
                                dbc.Col(
                                    dcc.Input(id='dolar-A', 
                                                    value=VA, 
                                                    style={"width": 50, "height": 30},)
                                ),
                                dbc.Col(),
                                ]),                         
                                ]),  className="m-4"), xl=10),
                dbc.Col(),
            ]), 
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([
                                html.H3(dbc.Badge('Patas B', color='warning', className="me-3")),
                                html.Hr(),
                            dbc.Row([
                                dbc.Col(
                                    html.H5('US$/kg:'),
                                ),
                                dbc.Col(
                                    dcc.Input(id='dolar-B', 
                                                    value=VB, 
                                                    style={"width": 50, "height": 30},)
                                ),
                                dbc.Col(),
                                ]),                         
                                ]),  className="m-4"), xl=10),
                dbc.Col(),
            ]), 
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([
                                html.H3(dbc.Badge('Patas C', color='danger', className="me-3")),
                                html.Hr(),
                            dbc.Row([
                                dbc.Col(
                                    html.H5('US$/kg:'),
                                ),
                                dbc.Col(
                                    dcc.Input(id='dolar-C', 
                                                    value=VC, 
                                                    style={"width": 50, "height": 30},)
                                ),
                                dbc.Col(),
                                ]),                         
                                ]),  className="m-4"), xl=10),
                dbc.Col(),
            ]),          
            html.Hr(style={'margin-left':'100px','margin-right':'100px'}),
            html.H5('Cotação do dólar:', style={'margin-left':'10px'}),
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([
                                html.H3(dbc.Badge('Conversão', color='primary', className="me-3")),
                                html.Hr(),
                            dbc.Row([
                                dbc.Col(
                                    html.H5('R$/US$:'),
                                ),
                                dbc.Col(
                                    dcc.Input(id='conv', 
                                                    value=USS, 
                                                    style={"width": 50, "height": 30},)
                                ),
                                dbc.Col(),
                                ]),                         
                                ]),  className="m-4",id='teste'), xl=10),
                dbc.Col(),
            ]), 
            dbc.Row([
                dbc.Col([
                    dbc.Button("Exportar", className="mr-1", style={'margin': '20px'}, id="export-button", n_clicks=0),
                    dcc.Download(id="pdf-download"),
                ], xl = 8),
                dbc.Col(),
            ])
            
        ],  className="m-0", style={"border":"none"},id = "capture-card"),
        ],xl = 2),
    dbc.Col(
    dbc.Container([

    #html.Hr(),
    dbc.Card(  # cabeçalho
        dbc.Row([            
                dbc.Row(html.H3('Contagem e Qualidade', style={'margin-left':'20px','margin-top':'20px'})),
                dbc.Row(html.H5('Unidade São Sebastião do Caí', style={'margin-left':'20px','margin-top':'2px'}))
            ], align="center"),
    ),  # fim do cabeçalho
    # dcc.Store(id='screen-size-store'),
    # dcc.Interval(id='screen_size_interval', interval=1000, n_intervals=0, max_intervals=1),  # Interval runs once on load
    html.Hr(),

    dcc.Tabs(id="tabs", value='tab-dia', children=[
        dcc.Tab(label='Dados diários', value='tab-dia'),
        dcc.Tab(label='Histórico', value='tab-historico'),
        dcc.Tab(label='Integrado', value='tab-financeiro'),
        dcc.Tab(label='Upload', value='tab-upload'),
    ]),
    html.Div(id='tabs-content')
    ],style={"padding": "20px", "margin": "10px","margin-right": "10px"},  # 5px border thickness
    className="border-primary rounded",  # Optional: set border color and rounded corners
    fluid=True  # Optional: full-width container
), xl = 9 ),    
])

        # Flask route to save the image data and generate PDF


@app.route("/save-image", methods=["POST"])
def save_image():
    data = request.get_json()
    image_data = data["imageData"].split(",")[1]
    image_bytes = BytesIO(base64.b64decode(image_data))
    print('Hello from save_image()')

    # Create PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.image(image_bytes, x=10, y=10, w=180)  # Adjust dimensions as needed
    pdf_output = BytesIO()
    pdf.output(pdf_output, 'F')
    pdf_output.seek(0)

    # Send the PDF file to download
    return send_file(pdf_output, mimetype="application/pdf", as_attachment=True, download_name="exported_card.pdf")


# Callback to switch between tabs and render content
@dash_app.callback(
    Output('tabs-content', 'children'),
    [Input('tabs', 'value')]
)
def render_tab_content(tab):
    global ffmpeg_process, ffmpeg_process2
    # Check if both RTSP streams are running before starting new ones
    stream_status = tab_functions.are_ffmpeg_streams_running(rtsp_streams)

    if tab == 'tab-dia':
        global TD, YY, MM, DD, CT         
        TD, YY, MM, DD, CT = tab_functions.update_today()
        if not all(stream_status.values()):
            # If either of the streams is not running, start the ffmpeg processes
            if not stream_status['rtsp://127.0.0.1:5202/ds-test']:
                ffmpeg_command = [
                    '/usr/bin/ffmpeg', 
                    '-rtsp_transport', 'tcp', 
                    '-i', 'rtsp://127.0.0.1:5202/ds-test', 
                    '-vcodec', 'libx264', 
                    '-f', 'flv', 
                    '-r', '10', 
                    '-s', '640x480', 
                    '-an', 'rtmp://localhost:1935/live/ds-test'
                ]
                ffmpeg_process = subprocess.Popen(ffmpeg_command)
            
            if not stream_status['rtsp://127.0.0.1:5203/ds-test-2']:
                ffmpeg_command2 = [
                    '/usr/bin/ffmpeg', 
                    '-rtsp_transport', 'tcp', 
                    '-i', 'rtsp://127.0.0.1:5203/ds-test-2', 
                    '-vcodec', 'libx264', 
                    '-f', 'flv', 
                    '-r', '10', 
                    '-s', '640x480', 
                    '-an', 'rtmp://localhost:1935/live/ds-test-2'
                ]
                ffmpeg_process2 = subprocess.Popen(ffmpeg_command2)
        else:
            print("Both ffmpeg streams are already running. Skipping process initialization.")
        return dia_tab_v2.layout  # Render the financeiro tab content
    
    elif tab == 'tab-historico':
        if stream_status['rtsp://127.0.0.1:5202/ds-test'] and ffmpeg_process is not None:
            ffmpeg_process.terminate()  # Stop the process if Tab 1 is active
            ffmpeg_process = None
        if stream_status['rtsp://127.0.0.1:5203/ds-test-2'] and ffmpeg_process2 is not None:    
            ffmpeg_process2.terminate()  # Stop the process if Tab 1 is active
            ffmpeg_process2 = None
        return historico_tab_v2.layout
    
    elif tab == 'tab-financeiro':
        if stream_status['rtsp://127.0.0.1:5202/ds-test'] and ffmpeg_process is not None:
            ffmpeg_process.terminate()  # Stop the process if Tab 1 is active
            ffmpeg_process = None
        if stream_status['rtsp://127.0.0.1:5203/ds-test-2'] and ffmpeg_process2 is not None:    
            ffmpeg_process2.terminate()  # Stop the process if Tab 1 is active
            ffmpeg_process2 = None
        return financeiro_tab_v2.layout
    
    elif tab == 'tab-upload':
        if stream_status['rtsp://127.0.0.1:5202/ds-test'] and ffmpeg_process is not None:
            ffmpeg_process.terminate()  # Stop the process if Tab 1 is active
            ffmpeg_process = None
        if stream_status['rtsp://127.0.0.1:5203/ds-test-2'] and ffmpeg_process2 is not None:    
            ffmpeg_process2.terminate()  # Stop the process if Tab 1 is active
            ffmpeg_process2 = None
        return upload_tab.layout


# Register callbacks from tab modules
financeiro_tab_v2.register_callbacks_financeiro(dash_app)
dia_tab_v2.register_callbacks(dash_app)
historico_tab_v2.register_callbacks(dash_app)
upload_tab.register_callbacks(dash_app)



if __name__ == '__main__':
    dash_app.run_server(debug=True)