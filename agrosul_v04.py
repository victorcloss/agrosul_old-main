
'''criar a tabela resumo e adicionar dados sempre que usuario fizer o upload de xlsb
quando usario pedir por uma data, tentar criar o resumo se não existir no banco de dados
se conseguir, mostrar na tela e adicionar no resumo'''

from dash import Dash, html, dcc, Output, Input, State, dash_table
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from flask import Flask
import plotly.graph_objs as go
import pandas as pd
from datetime import date, datetime, timedelta, time
import os
from io import BytesIO
import base64
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values
import pytz

from helper import get_date_picker_days, get_past_days

# Define the time zone for Brazil
time_zone = pytz.timezone('America/Sao_Paulo')

def update_today(tz):
    global today, YY, MM, DD, current_time

    # Get the current time in the time_zone
    current_time = datetime.now(tz)
    today = current_time.strftime('%Y-%m-%d')

    print('\n\n Today is '+today+'\n\n')

    #today = '2024-09-06'
    YY = int(current_time.strftime('%Y'))
    MM = int(current_time.strftime('%m'))
    DD = int(current_time.strftime('%d'))


update_today(time_zone)



# careful here, it seems this warning is irrelevant:
# https://stackoverflow.com/questions/71082494/getting-a-warning-when-using-a-pyodbc-connection-object-with-pandas
from warnings import filterwarnings
filterwarnings("ignore", category=UserWarning, message='.*pandas only supports SQLAlchemy connectable.*')

# dados da unidade Agrosul: 
unidade_id = 3
tempo_in_out = time(0, 4, 40) # define o tempo que leva da camera de entrada até a camera de saida
tempo_in_out_delta = timedelta(hours=tempo_in_out.hour, minutes=tempo_in_out.minute, seconds=tempo_in_out.second)


app = Flask(__name__)
dash_app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY, '/assests/styles.css'], url_base_pathname='/', server=app)
dash_app.title = 'THEIA'
dash_app._favicon = "icon.png"


################################################################# styles and graphs
# JavaScript code to get screen size on page load
'''dash_app.clientside_callback(
    """
    function(n_intervals) {
        return {'height': window.innerHeight, 'width': window.innerWidth};
    }
    """,
    Output('screen-size-store', 'data'),
    Input('screen_size_interval', 'n_intervals')  # Triggered when interval fires (on page load)
)'''


graph_style = {
    'font_family': 'Calibri',
    'fontSize': 20,
    'legendFontSize': 20,
    'titleFontSize': 16,
    'tickFontSize': 14,
}
colors = {'paw_a': '#18BC9C',
          'paw_b': '#F39C12',
          'paw_c': '#E74C3C',
          'Patas saida': '#2C3E50',
          'background': 'white',
          'text': '#7FDBFF',
          'primary': '#333e4e'}
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
                  marker=dict(colors=[colors['paw_a'], colors['paw_b'], colors['paw_c']])
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

    indices = df_carga.apply(lambda row: row.astype(str).str.contains('Placa', case=False, na=False)).any(axis=1)

    # Get the indices where the condition is True
    placa_indices = df_carga[indices].index.to_list()
    columns = ['Unnamed: 0', 'Unnamed: 2', 'Unnamed: 13', 'Unnamed: 22', 'Unnamed: 25']
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
    df_prev_cargas['Inicio do Abate'] = pd.to_datetime(df_prev_cargas['Inicio do Abate'], format='%H:%M:%S') - timedelta(hours=4)
    df_prev_cargas['Inicio do Abate'] = df_prev_cargas['Inicio do Abate'].dt.time

    df_prev_cargas.reset_index(drop=True, inplace=True)

    df_prev_cargas = df_prev_cargas.assign(Integrado=pd.Series(Integrado).values)
    df_prev_cargas = df_prev_cargas.assign(Lote=pd.Series(Lote).values)
    df_prev_cargas['Total de aves'] = df_prev_cargas['Aves na Carga']# - df_prev_cargas['Aves Mortas']

    return df_prev_cargas



# upload folder
UPLOAD_DIRECTORY = "uploads"
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)
################################################################# dados do excel binario [fim]
############################################### SQL

def get_df_a_p_carga(date_value):
    
    df_a=pd.DataFrame([]) 
    df_p=pd.DataFrame([])
    df_carga=pd.DataFrame([])

    try:
        excel_path = 'uploads/'+date_value+'.xlsb'
        # carrega arquivo agrosys
        df_carga = pd.read_excel(excel_path, engine='pyxlsb')
        # le a data
    except Exception as e:
        print(f'Arquivo {str(e)} não encontrado')
        df_carga = pd.DataFrame([])

        
    conn = psycopg2.connect(
        database="mytestdb",
        user="postgres",
        host="localhost",
        password="theia@24",
        port=5432
    )
    
    
    columns = ['hora', 'paw_a', 'paw_b', 'paw_c', 'chicken', 'hooks_empty']
    columns_str = ', '.join(columns)
    #Read only rows where 'data matches date_value
    query = f"SELECT {columns_str}  FROM paws WHERE data = '{date_value}'"
    df_p = pd.read_sql_query(query, conn)

    columns = ['hora', 'chicken', 'hooks_empty']
    columns_str = ', '.join(columns)
    #Read only rows where 'data matches date_value and only the columns specified above
    query = f"SELECT {columns_str}  FROM animals WHERE data = '{date_value}'"
    df_a = pd.read_sql_query(query, conn)

    conn.close()        

    return df_a, df_p, df_carga

def insert_dataframe_to_integrados(df):
    # Establish database connection
    conn = psycopg2.connect(
        database="mytestdb",
        user="postgres",
        host='localhost',
        password="theia@24",  
        port=5432
    )

    # Get unique dates from the DataFrame
    unique_dates = df['date'].unique()
    print('\n\n')
    print(df)
    print('\n\n')
    print(unique_dates)
    print('\n\n')

    try:
        # Create a cursor object
        cursor = conn.cursor()
        
        for date in unique_dates:

            delete_query = """
            DELETE FROM integrados WHERE date = %s;
            """
            cursor.execute(delete_query, (date,))
            print(f"Deleted existing entries for date: {date}")
        

        # Prepare the SQL insert query template
        insert_query = """
        INSERT INTO integrados (unidade_id, date, frangos_mortos, name, chicken, paw_a, paw_b, paw_c)
        VALUES %s
        """
        
        

        # Convert the DataFrame to a list of tuples
        values = [tuple(row) for row in df.itertuples(index=False, name=None)]
        print(values)
        print('\n\n')

        # Execute the bulk insert using execute_values
        execute_values(cursor, insert_query, values)

        # Commit the changes to the database
        conn.commit()
        print("DataFrame inserted successfully into the 'integrados' table.")

    except Exception as error:
        print(f"\n\nError: {error}\n\n")

    finally:
        # Close the cursor and connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def create_resumo(date_value):
    ''' This function recevies the date to compute resumo from the excell file and the data set
    '''
    global tempo_in_out_delta, unidade_id
    df_a, df_p, df_carga = get_df_a_p_carga(date_value)
    if df_a.empty or df_p.empty:
        return pd.DataFrame([]), False, False
    if df_carga.empty:
        return pd.DataFrame([]), True, False


    # AJUSTES DE df_p
    # ajusta a coluna da hora
    df_p['hora_shifted'] = pd.to_datetime(df_p['hora'], format='%H:%M:%S') - tempo_in_out_delta
    df_p['hora_shifted'] = pd.to_datetime(df_p['hora_shifted'], format='%H:%M:%S').dt.time
    # df_p['hora'] = pd.to_datetime(df_p['hora'], format='%H:%M:%S') - timedelta(hours=4)
    df_p['hora'] = pd.to_datetime(df_p['hora'], format='%H:%M:%S').dt.time
    
    # Create new columns to df_p
    t_zero = df_p['hora'].iloc[0].hour * 3600 + df_p['hora'].iloc[0].minute * 60 + df_p['hora'].iloc[
        0].second
    df_p['Tempo'] = df_p['hora'].apply(time_to_seconds) - t_zero
    df_p['dchicken'] = (df_p['chicken'].shift(10) - df_p['chicken'].shift(-10)) / (
            df_p['Tempo'].shift(10) - df_p['Tempo'].shift(-10))
    df_p['dhooks_empty'] = (df_p['hooks_empty'].shift(10) - df_p['hooks_empty'].shift(-10)) / (
            df_p['Tempo'].shift(10) - df_p['Tempo'].shift(-10))
    df_p['Indicador de Intervalo'] = df_p['dchicken'].apply(lambda x: 1 if x <= 0.3 else 0)

    

    # AJUSTES DE df_a
    df_a['hora'] = pd.to_datetime(df_a['hora'], format='%H:%M:%S').dt.time
    t_zero = df_a['hora'].iloc[0].hour * 3600 + df_a['hora'].iloc[0].minute * 60 + df_a['hora'].iloc[
        0].second
    df_a['Tempo'] = df_a['hora'].apply(time_to_seconds) - t_zero
    
    
    # Aggregating the values of 'chicken' in df_p, keeping the first occurrence of each 'hora'
    df_p_aggregated = df_p.groupby('hora')['chicken'].first()

    # Ensure that the result is a unique Series and set the index explicitly
    df_p_aggregated = pd.Series(df_p_aggregated)
    # copies chicken in df_p to df_a at the correct time slots    
    df_a['chicken out'] = df_a['hora'].map(df_p_aggregated)
    
    # now a copy shifted by time    
    # Aggregate the shifted values, ensuring uniqueness
    df_p_shifted_aggregated = df_p.groupby('hora_shifted')['chicken'].last()
    # Map the shifted 'Frango' values to 'chicken shifted' in df_a
    df_a['chicken shifted'] = df_a['hora'].map(df_p_shifted_aggregated)
    
    #agora a diferenca entre in e out
    df_a['dif'] = df_a['chicken']-df_a['chicken out']
    df_a['dif shifted'] = df_a['chicken']-df_a['chicken shifted']

    df_a['dchicken'] = (df_a['chicken'].shift(10) - df_a['chicken'].shift(-10)) / (
            df_a['Tempo'].shift(10) - df_a['Tempo'].shift(-10))    
    df_a['dchicken out'] = (df_a['chicken out'].shift(10) - df_a['chicken out'].shift(-10)) / (
            df_a['Tempo'].shift(10) - df_a['Tempo'].shift(-10))
    df_a['dchicken shifted'] = (df_a['chicken shifted'].shift(10) - df_a['chicken shifted'].shift(-10)) / (
            df_a['Tempo'].shift(10) - df_a['Tempo'].shift(-10))
    df_a['ddif shifted'] = (df_a['dif shifted'].shift(10) - df_a['dif shifted'].shift(-10)) / (
            df_a['Tempo'].shift(10) - df_a['Tempo'].shift(-10))   
    df_a['Indicador de Dif Elevada'] = df_a['ddif shifted'].apply(lambda x: 1 if x > 1 else 0)   
    df_a['Indicador de Parada'] = df_a['ddif shifted'].apply(lambda x: 1 if x == 0 else 0)  
             
    #print('\n\n')
    #print(df_p.iloc[15000:15030])
    #print('\n\n')
    #print(df_a.iloc[14990:15010])
    #print('\n\n')

    # %% ANÁLISE ENTRADA SAÍDA

    indice_trecho_final = round(len(df_a)*11/12)
    





    # %% RELATÓRIO DE CARGAS...
    # Find the index where the word 'placa' exists in the DataFrame
    indices = df_carga.apply(lambda row: row.astype(str).str.contains('Placa', case=False, na=False)).any(axis=1)

    # Get the indices where the condition is True
    placa_indices = df_carga[indices].index.to_list()
    columns = ['Unnamed: 0', 'Unnamed: 2', 'Unnamed: 13', 'Unnamed: 22', 'Unnamed: 25']
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

    # planilha interpretação do relatorio
    excel_path = 'uploads/'+date_value+'.xlsb'
    df_prev_cargas = get_previsao_carga(excel_path)
    df_prev_cargas_time_sorted = df_prev_cargas.sort_values(by='Inicio do Abate')

    #print('\n\n previsão de cargas:')
    #print(df_prev_cargas_time_sorted)

    # tabela total acumulado em ordem cronológica
    total_contagem = df_p['chicken'].iloc[-1]
    total_estimado = df_prev_cargas['Total de aves'].sum()
    discrepancia = total_contagem / total_estimado
    
    '''print('\n\n total contagem')
    print(total_contagem)
    print('\n\n total estimado')
    print(total_estimado)
    print('\n\n Discrepancia')
    print(discrepancia)
    print('\n\n')'''

    # df_acumulado['Lote'] = df_prev_cargas['Lote']
    data = [df_prev_cargas_time_sorted['Lote'].astype(int), (df_prev_cargas['Total de aves'] * discrepancia)]
    df_acumulado = pd.DataFrame(data)
    df_acumulado = df_acumulado.T
    df_acumulado.columns = ['Lote', 'chicken Ajustados']
    df_acumulado['Acumulado'] = df_acumulado['chicken Ajustados'].cumsum().astype(int)
    df_acumulado['chicken Ajustados'] = df_acumulado['chicken Ajustados'].astype(int)

    #print('\n\n df accu:')
    #print(df_acumulado)
    # %% até aqui bateu com "Cargas em Ordem Cronológica com totais acumulados"
    # ajuste dos dados acumulados com dados da contagem
    #print('\n\n data acc ajustada: [erro aqui nas trocas de lotes]')
    data_acc_ajustada = []
    for i in range(len(df_acumulado)):
        index = (df_p['chicken'] - df_acumulado['Acumulado'].iloc[
            i]).abs().idxmin()  # previsão do índice da troca de lote
           
        if i < len(df_acumulado) - 1 and int(df_acumulado['Lote'].iloc[i]) != int(df_acumulado['Lote'].iloc[i + 1]):
            # cum_troca_lote += 1
            interv = ([index - 60 * 2, index + 60 * 2])  # ajusta o indice em um intervalo de +-2min            
            index = df_p['Indicador de Intervalo'][interv[0]:interv[1]].idxmax()
            
        
        # print(index, int(df_p['chicken'].iloc[index]), int(df_p['paw_a'].iloc[index]))
        data_acc_ajustada.append([int(df_acumulado['Lote'].iloc[i]),
                                  int(df_p['chicken'].iloc[index]),  # qtd de chicken
                                  int(df_p['paw_a'].iloc[index]),  # Patas A
                                  int(df_p['paw_b'].iloc[index]),  # Patas B
                                  int(df_p['paw_c'].iloc[index]),  # Patas C
                                  df_p['hora'].iloc[index]
                                  ])

    
    
    # Print the DataFrame
    # print(pd.DataFrame(data_acc_ajustada))
    
    d = data_acc_ajustada
    data_por_carga = [d[0][:]]

    for i in range(len(data_acc_ajustada) - 1):
        data_por_carga.append(
            [d[i + 1][0], d[i + 1][1] - d[i][1], d[i + 1][2] - d[i][2], d[i + 1][3] - d[i][3], d[i + 1][4] - d[i][4]])

    df_por_carga = pd.DataFrame(data_por_carga)
    df_por_carga.columns = ['Lote', 'chicken', 'paw_a', 'paw_b', 'paw_c', 'hora']
    
    # print("\n\n df por carga:")
    # print(df_por_carga)

    data_datetime = pd.to_datetime(df_carga['Unnamed: 0'].iloc[6], origin='1899-12-30', unit='D')

    # tabela resumo do dia
    resumo = []
    mortos = 0
    for i in range(df_prev_cargas['Lote'].max()):
        Lote = i + 1
        index = df_prev_cargas['Lote'].loc[df_prev_cargas['Lote'] == Lote].index[0] if (
                df_prev_cargas['Lote'] == Lote).any() else -1
        nome = df_prev_cargas['Integrado'].iloc[index]
        chicken = int(df_por_carga.loc[df_por_carga['Lote'] == Lote, 'chicken'].sum())
        PA = int(df_por_carga.loc[df_por_carga['Lote'] == Lote, 'paw_a'].sum())
        PB = int(df_por_carga.loc[df_por_carga['Lote'] == Lote, 'paw_b'].sum())
        PC = int(df_por_carga.loc[df_por_carga['Lote'] == Lote, 'paw_c'].sum())
        resumo.append([unidade_id, data_datetime, mortos, nome, chicken, PA, PB, PC])

    df_resumo = pd.DataFrame(resumo)
    df_resumo.columns = ['unidade_id', 'date', 'frangos_mortos', 'name', 'chicken', 'paw_a', 'paw_b', 'paw_c']
    #Table Integrados = ([unidade_id,    date,   frangos_mortos,   name,   chicken,   paw_a,   paw_b,  paw_c])
 
    print('\nResumo do dia ' + date_value + ' criado:')
    print(df_resumo)

    return df_resumo, True, True

def get_resumo_dia(date_value):
    conn = psycopg2.connect(database="mytestdb",
                            user="postgres",
                            host='localhost',
                            password="theia@24",
                            port=5432)
    
    query = f"SELECT * FROM Integrados WHERE date = '{date_value}'"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_resumo_range(start_date, end_date):
    conn = psycopg2.connect(database="mytestdb",
                            user="postgres",
                            host='localhost',
                            password="theia@24",
                            port=5432)
    
    query = f"SELECT * FROM Integrados WHERE date >= '{start_date}' AND date <= '{end_date}'"
    df = pd.read_sql_query(query, conn)
    # print(df)
    # Aggregate by 'name'
    aggregated_df = df.groupby('name').agg({
        'chicken': 'sum',
        'paw_a': 'sum',
        'paw_b': 'sum',
        'paw_c': 'sum'
    }).reset_index()

    aggregated_df['Nota'] = round(3 * aggregated_df['paw_a'] / (aggregated_df['paw_a']+aggregated_df['paw_b']+aggregated_df['paw_c']) + 7 * (
                1 - aggregated_df['paw_c'] / (aggregated_df['paw_a']+aggregated_df['paw_b']+aggregated_df['paw_c'])), 2)


    conn.close()
    return aggregated_df

def ckech_resumo_db():
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

        # Define the table name
        table_name = 'resumo'

        # Check if the table exists
        check_table_query = sql.SQL(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
            """
        )

        cursor.execute(check_table_query, (table_name,))
        table_exists = cursor.fetchone()[0]

        print('testing resumo')
        # If the table does not exist, create it
        if not table_exists:
            print('creating resumo')
            create_table_query = sql.SQL(
                """
                CREATE TABLE {} (
                    id SERIAL PRIMARY KEY,
                    data TEXT
                )
                """
            ).format(psycopg2.Identifier(table_name))

            cursor.execute(create_table_query)
            print(f"Table '{table_name}' created successfully.")
        else:
            print(f"Table '{table_name}' already exists.")

        # Commit the transaction
        conn.commit()

        cursor.execute("SELECT DISTINCT data FROM Resumo")
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
                    #if file_date in db_data_dates:
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

def compute_chicken_before(df_a):
    global tempo_in_out_delta
    # Convert the 'time' column to datetime.datetime to enable arithmetic
    df_a['time_as_datetime'] = df_a['hora a'].apply(lambda t: datetime.combine(datetime.today(), t))
    


    last_time = df_a['time_as_datetime'].iloc[-1]
    adjusted_time = last_time - tempo_in_out_delta



    # Find the nearest 'time' in the DataFrame
    nearest_idx = (df_a['time_as_datetime'] - adjusted_time).abs().idxmin()
    chicken_before = df_a['chicken'].iloc[nearest_idx]

    '''print('nearest Index:')   
    print('\n\n now: ')
    print(last_time, len(df_a))
    print(' ago: ')
    print(adjusted_time, nearest_idx)
    print('\n\n chicken: '+str(df_a['chicken'].iloc[-1]))
    print('chicken_before: '+str(chicken_before)+'\n\n')'''
    return chicken_before

def read_today_data():
    #global today, YY, MM, DD
    
    conn = psycopg2.connect(database="mytestdb",
                            user="postgres",
                            host='localhost',
                            password="theia@24",
                            port=5432)
    #conn = sqlite3.connect(db_path)
    # Read only rows where 'data matches today's date
        # chicken comes from camera 1 tabel 'animals'
        # everything else from cam 2  table 'paws'
    columns = ['hora', 'chicken']
    columns_str = ', '.join(columns)
    #Read only rows where 'data matches today's date and only the columns specified above
    query = f"SELECT {columns_str}  FROM animals WHERE data = '{today}'"
    df_a = pd.read_sql_query(query, conn)

    columns = ['hora', 'paw_a', 'paw_b', 'paw_c', 'hooks_empty']
    columns_str = ', '.join(columns)
    #Read only rows where 'data matches today's date and only the columns specified above
    query = f"SELECT {columns_str}  FROM paws WHERE data = '{today}'"
    df_p = pd.read_sql_query(query, conn)
    conn.close()

    df_a=df_a.rename(columns={"hora": "hora a"}, errors='raise')
    df_p=df_p.rename(columns={"hora": "hora p"}, errors='raise')

    df_a.sort_values(['hora a'])
    df_p.sort_values(['hora p'])

    print('\npaws:')
    print(df_p)
    print('\n')
    print('animals:')
    print(df_a)
    print('\n')


    return df_p, df_a

def get_data_with_date(df_p, df_a, date_value):
    """ here we access the database and get df_p and df_a according to date_value"""    
    print(f'\n\nReading date from {date_value}')
    
    # Query the database 
    conn = psycopg2.connect(database="mytestdb",
                            user="postgres",
                            host='localhost',
                            password="theia@24",
                            port=5432)

    # Read only rows where 'data matches today's date
        # chicken comes from camera 1 tabel 'animals'
        # everything else from cam 2  table 'paws'
    columns = ['hora', 'chicken']
    columns_str = ', '.join(columns)
    #Read only rows where 'data matches value_date's date and only the columns specified above
    query = f"SELECT {columns_str}  FROM animals WHERE data = '{date_value}'"
    df_a = pd.read_sql_query(query, conn)
    


    columns = ['hora', 'paw_a', 'paw_b', 'paw_c', 'hooks_empty']
    columns_str = ', '.join(columns)
    #Read only rows where 'data matches value_date's date and only the columns specified above
    query = f"SELECT {columns_str}  FROM paws WHERE data = '{date_value}'"
    df_p = pd.read_sql_query(query, conn)
    conn.close()

    df_a = df_a.rename(columns={"hora": "hora a"}, errors='raise')
    df_p = df_p.rename(columns={"hora": "hora p"}, errors='raise')

    return df_p.sort_values(by=['hora p']), df_a.sort_values(by=['hora a'])

def update_data(df_p, df_a):
    """ here we access the database and update hour working dataframe df_p and df_a, if DataFrame is empty, read today's data"""    
    print('\n\nin update data')
    print(today)
    if df_p.empty or df_a.empty:
        print("\n\n DataFrame is empty, reading today's data.\n\n")
        df_p, df_a = read_today_data()
        return df_p, df_a

    #Get the last 'hora' entry in the DataFrame

    df_p = df_p.sort_values(['hora p'])
    df_a = df_a.sort_values(['hora a'])
    
    last_time_a = df_a['hora a'].iloc[-1]
    last_time_p = df_p['hora p'].iloc[-1]


    print('\nLast entry:')
    print('  - database ANIMALS\t '+last_time_a.strftime("%H:%M:%S"))
    print('  - database PAWS\t '+last_time_p.strftime("%H:%M:%S")+'\n')

    # Query the database for rows with 'hora' greater than the last_time
    conn = psycopg2.connect(database="mytestdb",
                            user="postgres",
                            host='localhost',
                            password="theia@24",
                            port=5432)
    #conn = sqlite3.connect(db_path)
    #query = f"SELECT * FROM {table_name} WHERE data = '{today}' AND hora IS NOT NULL AND hora > '{last_time}'"

    # Read only rows where 'data matches today's date
        # chicken comes from camera 1 tabel 'animals'
        # everything else from cam 2  table 'paws'
    columns = ['hora', 'chicken']
    columns_str = ', '.join(columns)
    #Read only rows where 'data matches today's date and only the columns specified above
    query = f"SELECT {columns_str}  FROM animals WHERE data = '{today}' AND hora IS NOT NULL AND hora > '{last_time_a}'"
    df_a2 = pd.read_sql_query(query, conn)
    


    columns = ['hora', 'paw_a', 'paw_b', 'paw_c', 'hooks_empty']
    columns_str = ', '.join(columns)
    #Read only rows where 'data matches today's date and only the columns specified above
    query = f"SELECT {columns_str}  FROM paws WHERE data = '{today}' AND hora IS NOT NULL AND hora > '{last_time_p}'"
    df_p2 = pd.read_sql_query(query, conn)
    conn.close()

    df_a2 = df_a2.rename(columns={"hora": "hora a"}, errors='raise')
    df_a2.sort_values(['hora a'])
    df_p2 = df_p2.rename(columns={"hora": "hora p"}, errors='raise')
    df_p2.sort_values(['hora p'])




    # Append new rows if there are any
    if not df_a2.empty:
        print(f"Found {len(df_a2)} new rows in chicken. Updating DataFrame.")
        df_a = pd.concat([df_a, df_a2], ignore_index=True)
    else:
        print("No new chicken rows found.")
    if not df_p2.empty:
        print(f"Found {len(df_p2)} new rows in paws. Updating DataFrame.")
        df_p = pd.concat([df_p, df_p2], ignore_index=True)
    else:
        print("No new paw rows found.")


    return df_p.sort_values(by=['hora p']), df_a.sort_values(by=['hora a'])



#df_paws columns = (['data, 'hora', 'Frame', 'chicken', 'paw_a', 'paw_b', 'paw_c', 'PawX',
#                      'FullHooks', 'SemiHooks', 'EmptyHooks', 'Synced', 'SyncDateTime'],
############################################### SQL [FIM]
############################################### variaveis
# create the data frame df_paws and df_animals -this will copy all rows from the database that correspond to the current date
df_paws, df_animals = read_today_data()
df_last_days = get_past_days(18)
print(f'\n\n Dados dos ultimos dias\n {df_last_days}')

if not df_paws.empty and not df_animals.empty:
    A = df_paws['paw_a'].iloc[-1]
    B = df_paws['paw_b'].iloc[-1]
    C = df_paws['paw_c'].iloc[-1]
    Total = df_animals['chicken'].iloc[-1]
else:
    A = 0
    B = 0
    C = 0
    Total = 0




############################################### variaveis [fim]

bar_layout = define_bar_layout()

bar_layout_dia = go.Layout(barmode='group',
                     title={'text': 'Desempenho nos últimos dias'},
                     yaxis=dict(automargin=True, ticksuffix="  "),
                     xaxis={'tickangle': 0, 'tickfont': {'size': 14}},
                     font_family=font_family,
                     font={'size': 20},
                     hoverlabel=dict(
                         font_size=20,
                         font_family=font_family)
                     )


dis_day_integrados, st_day_integrados, end_day_integrados = get_date_picker_days('integrados', 'chicken', 'date')
dis_day_paws, st_day_paws, end_day_paws = get_date_picker_days('paws', 'chicken', 'data')




dash_app.layout = dbc.Container([ 
    html.Hr(),
    dbc.Card(  # cabeçalho
        dbc.Row([
            dbc.Col(html.Img(src=r'assets/logo.png', className='responsive-img'),
		xs=6, sm=4, md=4, lg=4, xl=4
		),
            dbc.Col([
                dbc.Row(html.H3('Contagem e Qualidade')),
                dbc.Row(html.H5('Un. São Sebastião do Caí'))
            ], xs = 6, sm = 8, md = 8, lg=6, xl=6),
        ], align="center"),
    ),  # fim do cabeçalho
    # dcc.Store(id='screen-size-store'),
    # dcc.Interval(id='screen_size_interval', interval=1000, n_intervals=0, max_intervals=1),  # Interval runs once on load
    html.Hr(),
    dcc.Interval(id='dia-atualiza dados', interval=60000, n_intervals=0),
    dcc.Tabs([


        dcc.Tab(  # inicio aba 1 - dados diario
            dbc.Card([
                dbc.Row([
                     dcc.DatePickerSingle(
                        month_format='MMM YYYY',
                        display_format='DD/MM/2024',    
                        id='date-picker-dia',
                        min_date_allowed=st_day_paws,
                        max_date_allowed=end_day_paws,
                        initial_visible_month=today,  # To make sure the calendar starts on a month that has valid dates
                        disabled_days=dis_day_paws,
                        date=today
        )
                ]),
                dbc.Row([
                  dbc.Col(
                    dbc.Card(dbc.CardBody([
                        html.H5('Frangos', className='text-title'),
                        html.H3(dbc.Badge(Total, color='primary', className="me-3", id='dia-badge-total'))]),
                    ), xs=6, sm=6, md=2, lg=2
                  ),
                  dbc.Col(
                    dbc.Card(dbc.CardBody([
                        html.H5('Patas na saída ', className='text-title'),
                        html.H3(dbc.Badge(A + B + C, color='blue', className="me-3", id='dia-badge-patas'))]),
                    ),xs=6, sm=6, md=2, lg=2
                  ),
                  dbc.Col(
                    dbc.Card(dbc.CardBody([
                        html.H5('Patas Perdidas ', className='text-title'),
                        html.H3(dbc.Badge(Total * 2 - (A + B + C), color='danger', className="me-3",
                                          id='dia-badge-perdidas'))]),
                    ),xs=6, sm=6, md=2, lg=2
                  ),
                  dbc.Col(
                    dbc.Card(dbc.CardBody([
                        html.H5('Patas A \t  ', className='text-title'),
                        html.H3(dbc.Badge(A, color='success', className="me-3", id='dia-badge-A'), )]),
                    ),xs=6, sm=6, md=2, lg=2
                  ),
                  dbc.Col(
                    dbc.Card(dbc.CardBody([
                        html.H5('Patas B ' + '      ', className='text-title'),
                        html.H3(dbc.Badge(B, color='warning', className="me-3", id='dia-badge-B'), )]),
                    ),xs=6, sm=6, md=2, lg=2
                  ),
                  dbc.Col(
                    dbc.Card(dbc.CardBody([
                        html.H5('Patas C ', className='text-title'),
                        html.H3(dbc.Badge(C, color='danger', className="me-3", id='dia-badge-C')),]
                        , style={'justify-content': 'center'},),
                    ),xs=6, sm=6, md=2, lg=2
                  ),
                ], id='dia-dados'),

                dbc.Row([
                    dbc.Col(
                        dcc.Graph(id='dia-Frango Total', style={'display': 'none'}),
                        xs=12, sm=12, md = 12, lg = 7, xl = 7),
                    dbc.Col(dcc.Graph(id='dia-Pes-pie', style={'display': 'none'}),
                        xs=12, sm=12, md = 12, lg = 5, xl = 5)
                ]),
                dbc.Row([
                    dbc.Row(dcc.Graph(id='dia-Historico', style={'display': 'none'})),
                ]),
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
                    ], xs=12, sm=12, md=4, lg=3, xl=3),
                    dbc.Col([
                        dbc.Row(html.H5("Mostrar dados ordenados por:")),
                        dbc.Row(dcc.RadioItems(["ordem alfabética", "volume", "nota"], 'ordem alfabética',
                                               id='historico-ordem',
                                               style={'font-size': 18},
                                               inputStyle={"margin-right": "20px"}))
                    ], xs=12, sm=12, md=4, lg=4, xl=3),                    
                ], justify="start"),
                dbc.Row(html.Div(id='historico-text')),
                dbc.Row(dcc.Graph(id='historico-plot', style={'display': 'none'})),
                html.Hr(),
                dbc.Row(dcc.Graph(id='integrado-plot', style={'margin-right': '100px', 'border': '0px black solid', 'display': 'none'})),    
                ], body=True, outline=False),            
            label='Histórico', id='historico-tab'),  # fim aba historico por periodo

        dcc.Tab(  # inicio aba financeiro
            dbc.Card([            
                dbc.Row([
                        dbc.Col(
                            dbc.Card(dbc.CardBody([
                                html.H3(dbc.Badge('Patas A', color='success', className="me-3", id='valor-A')),
                                html.Hr(),
                            dbc.Row([
                                dbc.Col(
                                    html.H5('US$/kg:'),
                                ),
                                dbc.Col(
                                    dcc.Input(id='dolar-A', 
                                                    value='3.80', 
                                                    style={"width": 50, "height": 30},)
                                )]),                         
                                ]),
                            ),xs=6, sm=6, md=2, lg=2
                        ),
                        dbc.Col(
                            dbc.Card(dbc.CardBody([
                                html.H3(dbc.Badge('Patas B', color='warning', className="me-3", id='valor-B')),
                                html.Hr(),
                            dbc.Row([
                                dbc.Col(
                                    html.H5('US$/kg:'),
                                ),
                                dbc.Col(
                                    dcc.Input(id='dolar-B', 
                                                    value='3.50', 
                                                    style={"width": 50, "height": 30},)
                                )]),                         
                                ]),
                            ),xs=6, sm=6, md=2, lg=2
                        ),
                        dbc.Col(
                            dbc.Card(dbc.CardBody([
                                html.H3(dbc.Badge('Patas C', color='danger', className="me-3", id='valor-C')),
                                html.Hr(),
                                dbc.Row([
                                    dbc.Col(
                                        html.H5('US$/kg:'),
                                    ),
                                    dbc.Col(
                                        dcc.Input(id='dolar-C', 
                                                        value='3.30', 
                                                        style={"width": 50, "height": 30}),
                                    )]),                         
                                ]),
                            ),xs=6, sm=6, md=2, lg=2
                        ),
                        dbc.Col(
                            dbc.Card(dbc.CardBody([
                                html.H3(dbc.Badge('Peso/pata', color='primary', className="me-3", id='valor-peso')),
                                html.Hr(),
                                dbc.Row([
                                    dbc.Col(
                                        html.H5('kg:'), xs=6, sm=6, md=2, lg=4
                                    ),
                                    dbc.Col(
                                        dcc.Input(id='peso', 
                                                value='0.05', 
                                                style={"width": 50, "height": 30}),
                                    xs=6, sm=6, md=2, lg=4
                                    ),
                                    ]),                         
                                ]),
                            ),xs=6, sm=6, md=2, lg=2
                        ),
                    ]),
                                    
                html.Hr(),

                dbc.Row([                                   
                    dbc.Col([
                            dbc.Row(html.H4("Integrado:")),
                            dbc.Row(dcc.Dropdown(id='integrado-seletor', placeholder="Selecione um integrado"))
                        ],xs=12, sm=12, md=4, lg=4, xl=4),                    

                    ]),
                dbc.Row(html.Div(id='output-financeiro')),    

               
                
                ], body=True, outline=False),            
            label='Financeiro', id='financeiro-tab'),  # fim aba financeiro

        dcc.Tab(  # inicio upload
            dbc.Card([
                dbc.Row(dbc.Label("Para visualizar a tabela resumo, selecione a data:")),
                dbc.Row([
                    dbc.Col([
                        dcc.DatePickerSingle(
                            id='resumo-check',
                            month_format='MMM YYYY',
                            display_format='DD/MM/2024',
                            min_date_allowed=st_day_integrados,
                            max_date_allowed=today,
                            initial_visible_month=today,
                            disabled_days=dis_day_integrados,
                            date=today,
                        )], xs=12, sm=12, md=4, lg=4, xl=4),
                ]),
                dbc.Row(html.Div(id='output-resumo')),
                html.Hr(),
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
        label='Upload', id='dados-tab'),  # fim aba Dados

    ]),
    html.Hr(),
])
# Callback tab 'financeiro'
@dash_app.callback(
        Output('output-integrado','children'),
        Input("integrado-seletor", "value"),
)
def calback_finaneiro(nome):
    return nome



# Callback tab 'dados dia'
@dash_app.callback(    
    Output('dia-badge-total', 'children'),
    Output('dia-badge-patas', 'children'),
    Output('dia-badge-perdidas', 'children'),
    Output('dia-badge-A', 'children'),
    Output('dia-badge-B', 'children'),
    Output('dia-badge-C', 'children'),
    Output("dia-Frango Total", "figure"),
    Output("dia-Pes-pie", "figure"),
    Output("dia-Historico","figure"),
    Output('dia-Frango Total', 'style'),
    Output('dia-Pes-pie', 'style'),
    Output("dia-Historico","style"),
    Input("dia-atualiza dados", "n_intervals"),
    Input("date-picker-dia","date")
)
def atualiza_dados_dia(n_intervals, date_value):
    global df_paws, df_animals, df_last_days, today, tempo_in_out, time_zone
    
    # if the day changed we need to clear df_animals and df_paws
    if today != datetime.now(time_zone).strftime('%Y-%m-%d'):
        print('\n\n limpando os dados do dia anterior')
        df_animals.drop(df_animals.index, inplace=True)
        df_paws.drop(df_paws.index, inplace=True)
        update_today(time_zone)
    
    df_paws, df_animals = update_data(df_paws, df_animals)
    df_last_days = get_past_days(18)
    
    if date_value == today:
            if not df_paws.empty and not df_animals.empty:    
                A = df_paws['paw_a'].iloc[-1]
                B = df_paws['paw_b'].iloc[-1]
                C = df_paws['paw_c'].iloc[-1]
                # total chickens in
                Total = df_animals['chicken'].iloc[-1]        
                chicken_before = compute_chicken_before(df_animals)
                paws_lost = 2 * chicken_before - (A+B+C)

            else:
                A = 0
                B = 0
                C = 0
                Total = 0
                paws_lost = 0

                 
            df_p_display = df_paws
            df_a_display = df_animals
    else:
        df_p_display, df_a_display = get_data_with_date(df_paws, df_animals, date_value)
        if not df_p_display.empty and not df_a_display.empty:
            A = df_p_display['paw_a'].iloc[-1]
            B = df_p_display['paw_b'].iloc[-1]
            C = df_p_display['paw_c'].iloc[-1]
            # total chickens in
            Total = df_a_display['chicken'].iloc[-1]        
            chicken_before = compute_chicken_before(df_a_display)
            paws_lost = 2 * chicken_before - (A+B+C)

        else:
            A = 0
            B = 0
            C = 0
            Total = 0
            paws_lost = 0




        
    #df_paws.sort_values(['hora p'])
    #df_animals.sort_values(['hora a'])
    HH = pd.to_datetime(df_a_display['hora a'], format='%H:%M:%S').dt.strftime('%H:%M')
    trace_total_frangos = define_total_frangos_trace(HH, df_a_display['chicken'])
    
    if len(HH) < 10000:
        dtick = 15
    elif len(HH) < 20000:
        dtick = 30
    else:
        dtick = 60


        

    layout_total_frangos = define_total_frangos_layout(dtick)
    figure_total = {'data': [trace_total_frangos], 'layout': layout_total_frangos}



    

    trace_ABC_pizza = define_pie_trace([A, B, C], labels)
    layout_ABC_pizza = define_pie_layout(graph_style)
    figure_Pes_pie = {'data': [trace_ABC_pizza], 'layout': layout_ABC_pizza}


    #print('\n\n In fuction \n\n')
    #print(df_last_days)
   
    #print(df_last_days)

    trace_A = go.Bar(y=df_last_days['paw_a'], x=df_last_days['data']
                        ,name='Patas A', marker={'color': colors['paw_a']})
    trace_B = go.Bar(y=df_last_days['paw_b'], x=df_last_days['data']
                        ,name='Patas B', marker={'color': colors['paw_b']})
    trace_C = go.Bar(y=df_last_days['paw_c'], x=df_last_days['data']
                        ,name='Patas C', marker={'color': colors['paw_c']})
    trace_T = go.Bar(y=df_last_days['chicken'], x=df_last_days['data']
                        ,name='Total de Frangos', marker={'color': colors['primary']})
    style = {'margin-bottom': '10px',
                'margin-top': '10px',
                'margin-left': '30px',
                'margin-right': '20px',
                'height': 1000,
                'width': 1000,
                'border': '0px gray solid',
                'borderRadius': '15px',
                'ticksuffix': "  "
                }
    data_dias = [trace_A, trace_B, trace_C]


    figure_historico = {'data': data_dias, 'layout': bar_layout_dia}

   

    return  [Total, 
            (A + B + C), 
            paws_lost, 
            A, B, C, 
            figure_total, figure_Pes_pie, figure_historico,
            {'margin-right': '5px', 'border': '0px black solid'}, 
            {'margin-right': '5px', 'border': '0px black solid'},
            {'margin-right': '5px', 'border': '0px black solid'}]
# Callback tab 'dados dia' [fim]

# Callback tab 'show resumo'
@dash_app.callback(
    Output('output-resumo', 'children'),
    Input('resumo-check', 'date'))
def update_output_resumo(date_value):    
    
    df_resumo = get_resumo_dia(date_value)

    #print('\n\ncriando tabela\n\n')
    if not df_resumo.empty:
            
            df_display = df_resumo.iloc[:, 3:].copy()
            df_display.columns = ['Integrado', 'Frangos', 'Patas A', 'Patas B', 'Patas C']
            table = dash_table.DataTable(
	            data=df_display.to_dict('records'),
	            columns=[{"name": col, "id": col} for col in df_display.columns],
	            page_size=len(df_display.index),  # Adjust the page size as needed
	            style_table={'overflowX': 'auto'},
	            style_cell={'textAlign': 'left', 'padding': '5px'},
	            style_header={
	                'backgroundColor': 'rgb(230, 230, 230)',
        	        'fontWeight': 'bold'
	                }
	            )
            return html.Div([
#                    html.H5(' '),
#                    html.H5(f'Resumo do dia {str(date_value)}:'),
                    table
        	        ])
    
    return html.Div(html.H6(f"Sem dados para o dia."))
# Callback tab 'resumo' [fim]


# Callback tab 'upload dados'
@dash_app.callback(
    Output('output-upload', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
)
def save_uploaded_files(content, filename):
    global df_last_days
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
                

                if pd.isnull(data_datetime):
                    #print('\n\nNaT -> wrong file\n\n')
                    return html.Div([
                        html.H6(f'Arquivo .xlsb na formatação errada: a célula A8 deve conter a data.'),
                    ])

                
                new_name = data_datetime.strftime("%Y-%m-%d")
                print('\n\n'+new_name+'\n')

                # Save the file in the Uploads folder
                save_path = os.path.join('uploads', new_name + '.xlsb')
                with open(save_path, 'wb') as file:
                    file.write(decoded)

                df_prev = get_previsao_carga(save_path)
                # Create a DataTable to display the contents of the uploaded file
                table = dash_table.DataTable(
                    data=df_prev.to_dict('records'),
                    export_format="csv",
                    columns=[{"name": col, "id": col} for col in df_prev.columns],
                    page_size=len(df_prev.index),  # Adjust the page size as needed
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', 'padding': '5px'},
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold'
                    }
                )


                df_resumo, ok_dados, ok_file = create_resumo(new_name)
                print(new_name)
                print(df_resumo)
                if not df_resumo.empty:

                    print('\n\n Adicionando tabela resumo')
                    insert_dataframe_to_integrados(df_resumo)
                    


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
# Callback tab 'upload dados' [fim]


@dash_app.callback(
    Output('historico-text', 'children'),
    Output("historico-plot", "figure"),
    Output("historico-plot", "style"),
    [Input("historico-intervalo", "start_date"), Input("historico-intervalo", "end_date")],
    Input('historico-ordem', 'value'),  # seletor de ordenamento
    Input('historico-tab', 'id')  # Just a dummy input to trigger the callback once at the start
)
def atualiza_historico(start_date, end_date, ordem, _):
    if not start_date or not end_date:
        raise PreventUpdate
    df = get_resumo_range(start_date, end_date)
    '''print('\n\n')
    print(df)
    print('\n\n')
    print(df.columns)'''
    if df.empty:
        return html.H5('Sem dados no período'), {}, {'display': 'none'}, {}
    else:
        if ordem == 'ordem alfabética':
            df_aux = df.sort_values(by=['name'])
        if ordem == 'nota':
            df_aux = df.sort_values(by=['Nota'], ascending=False)
        if ordem == 'volume':
            df_aux = df.sort_values(by=['chicken'], ascending=False)
        trace_A = go.Bar(y=df_aux['name'] + ':  ' + df_aux['Nota'].astype(str), x=df_aux['paw_a'],
                         name='Patas A', marker={'color': colors['paw_a']}, width=.4, orientation='h')
        trace_B = go.Bar(y=df_aux['name'] + ':  ' + df_aux['Nota'].astype(str), x=df_aux['paw_b'],
                         name='Patas B', marker={'color': colors['paw_b']}, width=.4, orientation='h')
        trace_C = go.Bar(y=df_aux['name'] + ':  ' + df_aux['Nota'].astype(str), x=df_aux['paw_c'],
                         name='Patas C', marker={'color': colors['paw_c']}, width=.4, orientation='h')
        style = {'margin-bottom': '10px',
                 'margin-top': '10px',
                 'margin-left': '30px',
                 'margin-right': '20px',
                 'height': len(df) * 60 if len(df) > 6 else 7 * 60,
                 'width': 1000,
                 'border': '0px gray solid',
                 'borderRadius': '15px',
                 'ticksuffix': "  "
                 }
        data_integrados = [trace_C, trace_B, trace_A]
        figure = {'data': data_integrados, 'layout': bar_layout}

        # agora por integrado:




        return html.H5('Dados encontrados'), figure, style


'''
# Backend callback to display screen size
@dash_app.callback(
    # Output('output-div', 'children'),
    Input('screen-size-store', 'data')
)
def update_output(screen_size):
    if screen_size is None:
        return "Screen size not detected yet."
    

    width = screen_size['width']
    height = screen_size['height']
    
    print(f"\n\nScreen Width: {width}px, Screen Height: {height}px\n\n")
'''

if __name__ == '__main__':
    #dash_app.run(debug=True)
    app.run(host='127.0.0.1', port=8050)
    