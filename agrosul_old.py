from dash import Dash, html, dcc, callback, Output, Input, State, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
from datetime import date, datetime, timedelta
import os
from io import BytesIO
import base64
import psycopg2
import sqlite3
from flask import Flask

app = Flask(__name__)

dash_app = Dash(__name__, server=app,external_stylesheets=[dbc.themes.FLATLY], url_base_pathname='/')
dash_app.title = 'THEIA'
dash_app._favicon = "icon.png"


################################################################# styles and graphs
graph_style = {
    'font_family': 'Calibri',
    'fontSize': 20,
    'legendFontSize': 20,
    'titleFontSize': 16,
    'tickFontSize': 14,
}
colors = {'PawA': '#18BC9C',
          'PawB': '#F39C12',
          'PawC': '#E74C3C',
          'Patas saida': '#2C3E50',
          'background': 'white',
          'text': '#7FDBFF'}
labels = ['Pata A', 'Pata B', 'Pata C']
font_family = 'Calibri'


def define_total_frangos_trace(x, y):
    return go.Scatter(x=x, y=y, mode='lines')  # ,line = {'color':'Black', 'width':5})


def define_total_frangos_layout(dtick):
    return go.Layout(title='Frangos',
                     xaxis={'title': 'Horário', 'tickangle': 0, 'dtick': dtick},
                     hoverlabel=dict(
                         font_size=20,
                         font_family=font_family),
                     )


def define_pie_trace(val, labe):
    return go.Pie(values=val, labels=labe,
                  textinfo='label+percent',
                  # textfont_size=20,
                  sort=False,
                  pull=[0, 0, 0.2],
                  marker=dict(colors=[colors['PawA'], colors['PawB'], colors['PawC']])
                  )


def define_pie_layout(graph_style):
    return go.Layout(title='Qualidade',
                     legend={'traceorder': 'normal'},
                     hoverlabel=dict(
                         font_size=20,
                         font_family=font_family)
                     )


def define_bar_layout():
    return go.Layout(barmode='stack',
                     title={'text': 'Integrado e Nota', 'x': 0.05},
                     yaxis=dict(automargin=True, autorange='reversed', ticksuffix="  "),
                     xaxis={'tickangle': 0, 'tickfont': {'size': 14}},
                     font_family=font_family,
                     font={'size': 20},
                     hoverlabel=dict(
                         font_size=20,
                         font_family=font_family)
                     )

################################################################# styles and graphs [fim]
## ############################################################### dados do excel binario
# Function to convert timestampt to strin HH:MM:SS


def timestamp_to_str(time_as_stamp):
    timestamp = int(time_as_stamp * 86400)
    date_time = datetime.fromtimestamp(timestamp) + timedelta(hours=3)
    return date_time.strftime('%H:%M:%S')


def time_to_seconds(t):
    return t.hour * 3600 + t.minute * 60 + t.second


def get_previsao_carga(excel_path):
    # carrega arquivo agrosys
    df_carga = pd.read_excel(excel_path, engine='pyxlsb')

    # le a data
    data_datetime = pd.to_datetime(df_carga['Unnamed: 0'].iloc[6], origin='1899-12-30', unit='D')
    date_str = data_datetime.strftime('%d/%m/%Y')

    indices = df_carga.apply(lambda row: row.astype(str).str.contains('Placa', case=False, na=False)).any(axis=1)

    # Get the indices where the condition is True
    placa_indices = df_carga[indices].index.to_list()
    columns = ['Unnamed: 0', 'Unnamed: 2', 'Unnamed: 13', 'Unnamed: 21', 'Unnamed: 25']
    rows = []
    Integrado = []
    Lote = []
    j = 0
    for ii in placa_indices:  # how many cells with string 'placas' are there
        j = j + 1
        for i in range(ii + 3, len(df_carga)):  # three cells down (ii+3) we start to see the plate numbers
            if isinstance(df_carga['Unnamed: 0'].iloc[i], str) and len(df_carga['Unnamed: 0'].iloc[i]) == 7:
                rows.append(i)  # add if it looks like a plate
                Integrado.append(df_carga['Unnamed: 1'].iloc[ii - 1])
                Lote.append(j)
            else:
                break  # go to next produtor

    df_prev_cargas = df_carga.loc[rows, columns]
    df_prev_cargas.columns = ['Placa', 'Lote', 'Inicio do Abate', 'Aves na Carga', 'Aves Mortas']

    df_prev_cargas['Inicio do Abate'] = df_prev_cargas['Inicio do Abate'].apply(lambda x: timestamp_to_str(x))
    df_prev_cargas.reset_index(drop=True, inplace=True)

    df_prev_cargas = df_prev_cargas.assign(Integrado=pd.Series(Integrado).values)
    df_prev_cargas = df_prev_cargas.assign(Lote=pd.Series(Lote).values)
    df_prev_cargas['Total de aves'] = df_prev_cargas['Aves na Carga'] - df_prev_cargas['Aves Mortas']

    return df_prev_cargas


def create_resumo(excel_path, df):
    ''' This function recevies the excel file path and todays data and
    creates a table with the information that matters

    '''
    # carrega arquivo agrosys
    df_carga = pd.read_excel(excel_path, engine='pyxlsb')
    # le a data
    data_datetime = pd.to_datetime(df_carga['Unnamed: 0'].iloc[6], origin='1899-12-30', unit='D')
    date_str = data_datetime.strftime('%d/%m/%Y')
    # Colunas = 'Date', 'Time', 'Frame', 'Chicken', 'PawA', 'PawB', 'PawC', 'PawX',
    # 'FullHooks', 'SemiHooks', 'EmptyHooks', 'Synced', 'SyncDateTime'],

    # ajusta a coluna da hora
    df['Time'] = pd.to_datetime(df['Time'], format='%H:%M:%S').dt.time
    # Create new columns to df
    t_zero = df['Time'].iloc[0].hour * 3600 + df['Time'].iloc[0].minute * 60 + df['Time'].iloc[
        0].second
    df['Tempo'] = df['Time'].apply(time_to_seconds) - t_zero
    df['dChicken'] = (df['Chicken'] - df['Chicken'].shift(10)) / (
            df['Tempo'] - df['Tempo'].shift(10))
    df['dEmptyHooks'] = (df['EmptyHooks'] - df['EmptyHooks'].shift(10)) / (
            df['Tempo'] - df['Tempo'].shift(10))
    df['Indicador de Intervalo'] = df['dChicken'].apply(lambda x: 1 if x <= 0 else 0)

    # %%
    # Find the index where the word 'placa' exists in the DataFrame
    indices = df_carga.apply(lambda row: row.astype(str).str.contains('Placa', case=False, na=False)).any(axis=1)

    # Get the indices where the condition is True
    placa_indices = df_carga[indices].index.to_list()
    columns = ['Unnamed: 0', 'Unnamed: 2', 'Unnamed: 13', 'Unnamed: 21', 'Unnamed: 25']
    rows = []
    Integrado = []
    Lote = []
    j = 0
    for ii in placa_indices:  # how many cells with string 'placas' are there
        j = j + 1
        for i in range(ii + 3, len(df_carga)):  # three cells down (ii+3) we start to see the plate numbers
            if isinstance(df_carga['Unnamed: 0'].iloc[i], str) and len(df_carga['Unnamed: 0'].iloc[i]) == 7:
                rows.append(i)  # add if it looks like a plate
                Integrado.append(df_carga['Unnamed: 1'].iloc[ii - 1])
                Lote.append(j)
            else:
                break  # go to next produtor

    df_prev_cargas = get_previsao_carga(excel_path)
    df_prev_cargas_time_sorted = df_prev_cargas.sort_values(by='Inicio do Abate')

    # tabela total acumulado em ordem cronológica
    total_contagem = df['Chicken'].iloc[-1]
    total_estimado = df_prev_cargas['Total de aves'].sum()
    discrepancia = total_contagem / total_estimado

    # df_acumulado['Lote'] = df_prev_cargas['Lote']
    data = [df_prev_cargas_time_sorted['Lote'].astype(int), (df_prev_cargas['Total de aves'] * discrepancia)]
    df_acumulado = pd.DataFrame(data)
    df_acumulado = df_acumulado.T
    df_acumulado.columns = ['Lote', 'Chicken Ajustados']
    df_acumulado['Acumulado'] = df_acumulado['Chicken Ajustados'].cumsum().astype(int)
    df_acumulado['Chicken Ajustados'] = df_acumulado['Chicken Ajustados'].astype(int)

    # print(df_acumulado)
    # %%
    # ajuste dos dados acumulados com dados da contagem
    data_acc_ajustada = []
    for i in range(len(df_acumulado)):
        index = (df['Chicken'] - df_acumulado['Acumulado'].iloc[
            i]).abs().idxmin()  # previsão do índice da troca de lote
        if i < len(df_acumulado) - 1 and int(df_acumulado['Lote'].iloc[i]) != int(df_acumulado['Lote'].iloc[i + 1]):
            # cum_troca_lote += 1
            interv = ([index - 60 * 2, index + 60 * 2])  # ajusta o indice em um intervalo de +-2min
            index = df['Indicador de Intervalo'][interv[0]:interv[1]].idxmax()

        data_acc_ajustada.append([int(df_acumulado['Lote'].iloc[i]),
                                  int(df['Chicken'].iloc[index]),  # qtd de Chicken
                                  int(df['PawA'].iloc[index]),  # Patas A
                                  int(df['PawB'].iloc[index]),  # Patas B
                                  int(df['PawC'].iloc[index])  # Patas C
                                  ])

    d = data_acc_ajustada
    data_por_carga = [d[0][:]]

    for i in range(len(data_acc_ajustada) - 1):
        data_por_carga.append(
            [d[i + 1][0], d[i + 1][1] - d[i][1], d[i + 1][2] - d[i][2], d[i + 1][3] - d[i][3], d[i + 1][4] - d[i][4]])

    df_por_carga = pd.DataFrame(data_por_carga)
    df_por_carga.columns = ['Lote', 'Chicken', 'PawA', 'PawB', 'PawC']
    # print(df_por_carga)

    # tabela resumo do dia
    resumo = []
    for i in range(df_prev_cargas['Lote'].max()):
        Lote = i + 1
        index = df_prev_cargas['Lote'].loc[df_prev_cargas['Lote'] == Lote].index[0] if (
                df_prev_cargas['Lote'] == Lote).any() else -1
        nome = df_prev_cargas['Integrado'].iloc[index]
        Chicken = int(df_por_carga.loc[df_por_carga['Lote'] == Lote, 'Chicken'].sum())
        PA = int(df_por_carga.loc[df_por_carga['Lote'] == Lote, 'PawA'].sum())
        PB = int(df_por_carga.loc[df_por_carga['Lote'] == Lote, 'PawB'].sum())
        PC = int(df_por_carga.loc[df_por_carga['Lote'] == Lote, 'PawC'].sum())
        total = PA + PB + PC
        resumo.append([data_datetime, Lote, nome, Chicken, PA, PB, PC, total])

    df_resumo = pd.DataFrame(resumo)
    df_resumo.columns = ['Date', 'Lote', 'Integrado', 'Chicken', 'PawA', 'PawB', 'PawC', 'Patas Total']

    print('Resumo do dia ' + date_str + ' criado:')
    print(df_resumo)

    return df_resumo

# upload folder
UPLOAD_DIRECTORY = "uploads"
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)
################################################################# dados do excel binario [fim]
############################################### SQL


def update_resumo_db():
    global db_path
    '''This code checks if all files in directory upload were processed and are in Resumo table of the data base'''

    # Directory where the .xlsb files are stored
    uploads_folder = 'uploads'

    # Connect to the SQLite database
    conn = psycopg2.connect(database="mytestdb",
                            user="postgres",
                            host='localhost',
                            password="theia@24",
                            port=5432)
    #conn = sqlite3.connect(db_path)  # Update with your database path if necessary
    cursor = conn.cursor()

    # Fetch all unique dates from the "Date" column in the "Data" table
    cursor.execute("SELECT DISTINCT Date FROM Data")
    db_data_dates = {datetime.strptime(row[0], "%Y-%m-%d").date() for row in cursor.fetchall()}

    # Check if the table 'Resumo' exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Resumo';")
    table_exists = cursor.fetchone()

    # If the table does not exist, create an empty one with a 'Date' column
    if not table_exists:
        print("Table 'Resumo' does not exist. Creating an empty table...")
        cursor.execute("""
            CREATE TABLE Resumo (
                Date TEXT
            )
        """)
        conn.commit()

    cursor.execute("SELECT DISTINCT Date FROM Resumo")
    db_resumo_dates = {datetime.strptime(row[0], "%Y-%m-%d").date() for row in cursor.fetchall()}

    # Get the list of all .xlsb files in the uploads folder
    xlsb_files = [file for file in os.listdir(uploads_folder) if file.endswith('.xlsb')]

    # Extract dates from the file names and compare with database dates
    missing_dates = []
    for file in xlsb_files:
        try:
            # Extract date from file name (assuming format is DD-MM-YYYY.xlsb)
            file_date = datetime.strptime(file.replace('.xlsb', ''), "%Y-%m-%d").date()
            # Check if the date from the file is not in the database dates
            if file_date not in db_resumo_dates:
                if file_date in db_data_dates:
                    missing_dates.append(file_date)
        except ValueError:
            print(f"Skipping file with incorrect date format: {file}")

    # Print missing dates
    if missing_dates:
        print("Dates from files not found in the database:")
        for date in missing_dates:
            print(date.strftime("%Y-%m-%d"))
    else:
        print("All file dates are present in the database.")

    # Close the database connection
    cursor.close()
    conn.close()
    return


def read_today_data(db_path, table_name):
    today = datetime.now().strftime('%Y-%m-%d')  # Current date in YYYY-MM-DD format

    conn = psycopg2.connect(database="mytestdb",
                            user="postgres",
                            host='localhost',
                            password="theia@24",
                            port=5432)

    #conn = sqlite3.connect(db_path)
    # Read only rows where 'Date' matches today's date
    query = f"SELECT * FROM {table_name} WHERE Date = '{today}'"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def update_data(df, db_path, table_name):
    """ here we access the database and update hour working dataframe, if DataFrame is empty, read today's data"""
    if df.empty:
        print("DataFrame is empty, reading today's data.")
        df = read_today_data(db_path, table_name)
        return df

    # Get the last 'Time' entry in the DataFrame
    last_time = df['Time'].max()

    # Query the database for rows with 'Time' greater than the last_time
    conn = psycopg2.connect(database="mytestdb",
                            user="postgres",
                            host='localhost',
                            password="theia@24",
                            port=5432)
    #conn = sqlite3.connect(db_path)
    today = datetime.now().strftime('%Y-%m-%d')
    query = f"SELECT * FROM {table_name} WHERE Date = '{today}' AND Time > '{last_time}'"
    new_data = pd.read_sql_query(query, conn)
    conn.close()

    # Append new rows if there are any
    if not new_data.empty:
        print(f"Found {len(new_data)} new rows. Updating DataFrame.")
        df = pd.concat([df, new_data], ignore_index=True)
    else:
        print("No new rows found.")


    return df


# Define the database path and table name
db_path = 'local-database-cam1.db'
table_name = 'aws'
# create the data frame df_dados -this will copy all rows from the database that correspond to the current date
df_dados = read_today_data(db_path, table_name)
# df_dados columns = 'id', 'equipamento_id', 'data', 'hora', 'frame', 'chicken', 'paw_a',
#       'paw_b', 'paw_c', 'paw_x', 'hooks_full', 'hooks_semi', 'hooks_empty',
#       'created_at', 'updated_at']
###################################################### SQL [FIM]
###################################################### variaveis
if not df_dados.empty:
    A = df_dados['paw_a'].iloc[-1]
    B = df_dados['paw_b'].iloc[-1]
    C = df_dados['paw_c'].iloc[-1]
    Total = df_dados['chicken'].iloc[-1]
else:
    A = 0
    B = 0
    C = 0
    Total = 0

bar_layout = define_bar_layout()

last_updated_hour = None

######## Today
YY = int(datetime.today().strftime('%Y'))
MM = int(datetime.today().strftime('%m'))
DD = int(datetime.today().strftime('%d'))
############################################### variaveis [fim]

dash_app.layout = dbc.Container([
    html.Hr(),
    dbc.Card(  # cabeçalho
        dbc.Row([
            dbc.Col(html.Img(src=r'assets/logo.png', style={'height': '40%'}), width=3),
            dbc.Col([
                dbc.Row(html.H3('Contagem e Qualidade')),
                dbc.Row(html.H5('Unidade de São Sebastião do Caí'))
            ]),
        ], align="center"),
    ),  # fim do cabeçalho
    html.Hr(),
    dcc.Interval(id='dia-atualiza dados', interval=10000, n_intervals=0),
    dcc.Tabs([


        dcc.Tab(  # inicio aba 1 - dados diario
            dbc.Card([
                dbc.CardGroup([
                    dbc.Card(dbc.CardBody([
                        html.H5('Frangos na entrada', className='text-title'),
                        html.H3(dbc.Badge(Total, color='primary', className="me-3", id='dia-badge-total'))]),
                    ),
                    dbc.Card(dbc.CardBody([
                        html.H5('Patas na saída ', className='text-title'),
                        html.H3(dbc.Badge(A + B + C, color='blue', className="me-3", id='dia-badge-patas'))]),
                    ),
                    dbc.Card(dbc.CardBody([
                        html.H5('Patas Perdidas ', className='text-title'),
                        html.H3(dbc.Badge(Total * 2 - (A + B + C), color='danger', className="me-3",
                                          id='dia-badge-perdidas'))]),
                    ),
                    dbc.Card(dbc.CardBody([
                        html.H5('Patas A \t  ', className='text-title'),
                        html.H3(dbc.Badge(A, color='success', className="me-3", id='dia-badge-A'), )]),
                    ),
                    dbc.Card(dbc.CardBody([
                        html.H5('Patas B ' + '      ', className='text-title'),
                        html.H3(dbc.Badge(B, color='warning', className="me-3", id='dia-badge-B'), )]),
                    ),
                    dbc.Card(dbc.CardBody([
                        html.H5('Patas C ', className='text-title'),
                        html.H3(dbc.Badge(C, color='danger', className="me-3", id='dia-badge-C'))]
                        , style={'justify-content': 'center'}),
                    ),
                ], id='dia-dados'),

                dbc.Row([
                    dbc.Col(
                        dcc.Graph(id='dia-Frango Total', style={'margin-right': '25px', 'border': '0px black solid'}),
                        width=7),
                    dbc.Col(dcc.Graph(id='dia-Pes-pie', style={'margin-right': '100px', 'border': '0px black solid'}),
                            width=5)
                ])
            ], body=True, outline=False),
            label='Dados do dia'),  # fim da dia

        dcc.Tab(  # inicio aba historico por periodo
            dbc.Card([
                dbc.Row([
                    dbc.Col([
                        dbc.Row(html.H5("Selecione o intervalo:")),
                        dbc.Row(dcc.DatePickerRange(
                            id='historico-intervalo',
                            month_format='MMM YYYY',
                            display_format='DD/MM/2024',
                            min_date_allowed=date(2024, 1, 1),
                            max_date_allowed=date(YY, MM, DD),
                            initial_visible_month=date(YY, MM, DD),
                            end_date=date(YY, MM, DD)
                        ),),
                    ], width=4),
                    dbc.Col([
                        dbc.Row(html.H5("Mostrar dados ordenados por:")),
                        dbc.Row(dcc.RadioItems(["ordem alfabética", "volume", "nota"], 'ordem alfabética',
                                               id='historico-ordem',
                                               style={'font-size': 18},
                                               inputStyle={"margin-right": "20px"}))
                    ], width=4)
                ], justify="start"),
                dbc.Row(html.Div(id='historico-text')),
                dbc.Row(dcc.Graph(id='historico-plot', style={'dispaly': 'none'})),
            ], body=True, outline=False)
            , label='Histórico total', id='historico-tab'),  # fim aba historico por periodo

        dcc.Tab(  # inicio aba historico integrado
            dbc.Card([
                dbc.Row(dbc.Label("Selecione a data:")),
                dbc.Row([
                    dbc.Col([
                        dcc.DatePickerRange(
                            id='financeiro-intervalo',
                            month_format='MMM YYYY',
                            display_format='DD/MM/2024',
                            min_date_allowed=date(2024, 1, 1),
                            max_date_allowed=date(YY, MM, DD),
                            initial_visible_month=date(YY, MM, DD),
                            end_date=date(YY, MM, DD)
                        )], width=4),
                    dbc.Col([
                        dcc.Dropdown(id='financeiro-seletor', placeholder="Selecione um integrado")
                    ])
                ]),
                dbc.Row(dcc.Graph(id='financeiro-plot', style={'margin-right': '100px', 'border': '0px black solid'})),
            ], body=True, outline=False)
            , label='Histórico por Integrado', id='financeiro-tab'),  # fim aba historico integrado



        dcc.Tab([  # inicio aba Dados
            dbc.Card([
                dbc.Row(html.H5("Upload das planilhas em formato 'xlsb':")),
                html.Div([
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div([
                            'Arraste e solte ou aperte  ',
                            html.A('AQUI', href='#'),
                            '  para selecionar seus arquivos.',
                        ]),
                        style={
                            'width': '100%',
                            'height': '160px',
                            'lineHeight': '60px',
                            'borderWidth': '1px',
                            'borderStyle': 'dashed',
                            'borderRadius': '5px',
                            'textAlign': 'center',
                            'margin': '10px'
                        },
                        # Allow multiple files to be uploaded
                        multiple=False),
                ]),
                dbc.Row(html.Div(id='output-upload')),
            ], body=True, outline=False),
        ], label='Upload', id='dados-tab'),  # fim aba Dados
    ]),
    html.Hr(),
])


@dash_app.callback(
    Output("dia-Frango Total", "figure"),
    Output("dia-Pes-pie", "figure"),
    Output('dia-badge-total', 'children'),
    Output('dia-badge-patas', 'children'),
    Output('dia-badge-perdidas', 'children'),
    Output('dia-badge-A', 'children'),
    Output('dia-badge-B', 'children'),
    Output('dia-badge-C', 'children'),
    Input("dia-atualiza dados", "n_intervals"),
)
def atualiza_dados_dia(n_intervals):
    global df_dados
    df_dados = update_data(df_dados, db_path, 'Data')
    HH = pd.to_datetime(df_dados['Time'], format='%H:%M:%S').dt.strftime('%H:%M')
    trace_total_frangos = define_total_frangos_trace(HH, df_dados['Chicken'])
    if len(HH) < 10000:
        dtick = 15
    elif len(HH) < 20000:
        dtick = 30
    else:
        dtick = 60
    layout_total_frangos = define_total_frangos_layout(dtick)
    figure_total = {'data': [trace_total_frangos], 'layout': layout_total_frangos}

    if not df_dados.empty:
        A = df_dados['PawA'].iloc[-1]
        B = df_dados['PawB'].iloc[-1]
        C = df_dados['PawC'].iloc[-1]
        Total = df_dados['Chicken'].iloc[-1]
    else:
        A = 0
        B = 0
        C = 0
        Total = 0

    trace_ABC_pizza = define_pie_trace([A, B, C], labels)
    layout_ABC_pizza = define_pie_layout(graph_style)
    figure_Pes_pie = {'data': [trace_ABC_pizza], 'layout': layout_ABC_pizza}

    ### Here we update the resumo data every hour
    global last_updated_hour
    # Get the current hour
    current_time = datetime.now()
    current_hour = current_time.hour

    if current_hour != last_updated_hour:
        print('Atualizando banco de dados...')
        update_resumo_db()
        print('Banco de dados atualizado.')
        # Update the last printed hour
        last_updated_hour = current_hour

    return figure_total, figure_Pes_pie, Total, (A + B + C), Total * 2 - (A + B + C), A, B, C


# Callback tab 'upload'
@dash_app.callback(
    Output('output-upload', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
)
def save_uploaded_files(content, filename):
    if content is not None:
        if filename.endswith('.xlsb'):
            # Decode the file content
            data = content.split(',')[1]
            decoded = base64.b64decode(data)
            try:
                with BytesIO(decoded) as file:
                    df = pd.read_excel(file, engine='pyxlsb')

                # extract the date from the corresponding cell
                data_datetime = pd.to_datetime(df['Unnamed: 0'].iloc[6], origin='1899-12-30', unit='D')
                new_name = data_datetime.strftime("%Y-%m-%d")

                # Save the file in the Uploads folder
                save_path = os.path.join('uploads', new_name + '.xlsb')
                with open(save_path, 'wb') as file:
                    file.write(decoded)

                df_prev = get_previsao_carga(save_path)
                # Create a DataTable to display the contents of the uploaded file
                table = dash_table.DataTable(
                    data=df_prev.to_dict('records'),
                    columns=[{"name": col, "id": col} for col in df_prev.columns],
                    page_size=len(df_prev.index),  # Adjust the page size as needed
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', 'padding': '5px'},
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold'
                    }
                )

                return html.Div([
                    html.H6(f'Upload dos dados do abate do dia {str(new_name)} feito com sucesso:'),
                    table
                ])
            except Exception as e:
                return html.Div([
                    html.H6(f'Erro ao salvar o arquivo: {str(e)}'),
                ])
        else:
            return html.Div('Por favor, carregue arquivos no formato .xlsb.')

# Define a basic route for Flask
@app.route("/")
def hello():
    return redirect("/")


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8050)
