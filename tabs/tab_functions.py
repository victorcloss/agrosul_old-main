'''you can restrict the dcc.DatePickerSingle in Dash to show only certain available dates for selection. You can achieve this by using the min_date_allowed, max_date_allowed, and disabled_days properties of dcc.DatePickerSingle.

Here's how to configure it:

Example: Show Only Available Dates'''

import psycopg2
from datetime import timedelta, datetime, time
from psycopg2 import sql
from psycopg2.extras import execute_values
import pytz
import pandas as pd
import psutil

def get_unidade_id():
    agrosul_id = 3
    return agrosul_id # cada planta tera uma unidade

def get_tempo_in_out():
    # define o tempo que leva da camera de entrada até a camera de saida
    tempo_in_out = time(0, 4, 40) 
    tempo_in_out_delta = timedelta(hours=tempo_in_out.hour, 
                                   minutes=tempo_in_out.minute, 
                                   seconds=tempo_in_out.second)
    return tempo_in_out, tempo_in_out_delta

def update_today(time_zone='America/Sao_Paulo'):
    # Get the current time in the time_zone
    tz = pytz.timezone(time_zone)
    current_time = datetime.now(tz)
    today = current_time.strftime('%Y-%m-%d')

    #print('\n\n Today is '+today+'\n\n')

    yy = int(current_time.strftime('%Y'))
    mm = int(current_time.strftime('%m'))
    dd = int(current_time.strftime('%d'))
    return today, yy, mm, dd, current_time


# list of dates with problems in the data, instead of erasing the dataset, we create a blacklist
def get_blacklist_dates():
    return {'2024-09-03','2024-09-19','2024-09-20','2024-09-23',
            '2024-10-03','2024-10-09','2024-10-10','2024-10-11','2024-10-18','2024-10-21','2024-10-29',
            '2024-11-01','2024-11-15','2024-11-20','2024-11-21','2024-11-25',
            '2024-12-24','2024-12-25','2024-12-31',
            '2025-01-01','2025-01-20','2025-01-30','2025-01-29','2025-01-31',
            '2025-02-04'
            }

        

################################### funções ffmpeg
def are_ffmpeg_streams_running(stream_urls):
    """
    Check if ffmpeg processes with specific RTSP streams are running.
    
    Parameters:
        stream_urls (list): A list of RTSP stream URLs to check.
        
    Returns:
        dict: A dictionary where the keys are stream URLs and values are booleans indicating if they are running.
    """
    streams_status = {url: False for url in stream_urls}  # Initialize all streams as not running

    # Iterate over all running processes to check for ffmpeg with specific stream URLs
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'ffmpeg' in proc.info['name'] or any('ffmpeg' in cmd for cmd in proc.info['cmdline']):
                for url in stream_urls:                    
                    if proc.info['cmdline'] is not None and any(url in cmd for cmd in proc.info['cmdline']):
                        streams_status[url] = True  # Mark the stream URL as running
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass  # If there's an issue accessing process info, ignore and continue

    return streams_status


def kill_all_ffmpeg_processes():
    """
    Terminate all running ffmpeg processes on the server.
    """
    killed_processes = []  # List to keep track of terminated processes

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'ffmpeg' in proc.info['name'] or any('ffmpeg' in cmd for cmd in proc.info['cmdline']):
                proc.terminate()  # Send termination signal to the process
                killed_processes.append(proc.pid)  # Record the PID of the terminated process
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass  # Ignore errors when accessing or terminating a process

    if killed_processes:
        print(f"Terminated ffmpeg processes with PIDs: {killed_processes}")
    else:
        print("No ffmpeg processes found running.")

################################### funções ffmpeg
####################### estilos
'''graph_style = {
    'font_family': 'Calibri',
    'fontSize': 20,
    'legendFontSize': 20,
    'titleFontSize': 16,
    'tickFontSize': 14,
}'''
colors = {'paw_a': '#18BC9C',
          'paw_b': '#F39C12',
          'paw_c': '#E74C3C',
          'Patas saida': '#2C3E50',
          'background': 'white',
          'text': '#7FDBFF',
          'primary': '#333e4e'}
labels = ['Pata A', 'Pata B', 'Pata C']
font_family = 'Calibri'
####################### estilos [fim]

####################### fnc da aba dias
# computes first day where there is info and the days where there is no info, used in the datepicker 
def get_date_picker_days(table, column_zero, column_dates):
    today = update_today()
    

    conn = psycopg2.connect(database="mytestdb",
                            user="postgres",
                            host='localhost',
                            password="theia@24",
                            port=5432)
    cursor = conn.cursor()
    query = sql.SQL("""
        SELECT DISTINCT {column_dates}
        FROM {table}
        GROUP BY {column_dates}
        HAVING SUM({column_zero}) != 0;
        """).format(
    column_dates=sql.Identifier(column_dates),
    column_zero=sql.Identifier(column_zero),
    table=sql.Identifier(table)
    )
    cursor.execute(query)
    tuples= cursor.fetchall()
    available_dates = []
    for i in range(len(tuples)):
        A = tuples[i]
        available_dates.append(A[0])
    start_date = min(available_dates) 
    end_date = today[4].date()
    all_dates = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    disabled_dates = [d for d in all_dates if d not in available_dates]
    return disabled_dates, start_date, end_date

def get_days_range(start_date, end_date):
    if start_date is None or end_date is None:
        tz = pytz.timezone('America/Sao_Paulo')
        # Get the current time in the time_zone
        end_date = datetime.now(tz)
        # Generate a list of the past n_days days
        start_date =  (end_date - timedelta(days=10))
        #print(f'\n\n last day = {last_day.date}')
    conn = psycopg2.connect(database="mytestdb",
                            user="postgres",
                            host='localhost',
                            password="theia@24",
                            port=5432)
    cur = conn.cursor()

    # Query the database 
    columns = ['data', 'paw_a', 'paw_b', 'paw_c', 'hooks_empty']
    columns_str = ', '.join(columns)

    #Read only rows where 'data matches value_date's date and only the columns specified above
    query = '''SELECT DISTINCT ON (data)  data, paw_a, paw_b, paw_c 
            FROM paws 
            WHERE data >= %s AND data <= %s
            ORDER BY data, frame DESC'''
    
    # Execute the query with the parameterized last_data value
    cur.execute(query, (start_date, end_date))

    # Fetch all results
    rows = cur.fetchall()
    
    # Optionally convert the result to a pandas DataFrame for easier manipulation
    df = pd.DataFrame(rows, columns=[desc[0] for desc in cur.description])
    
    query = '''SELECT DISTINCT ON (data)  data, chicken 
            FROM animals 
            WHERE data >= %s AND data <= %s
            ORDER BY data, frame DESC'''
    
    # Execute the query with the parameterized last_data value
    cur.execute(query, (start_date, end_date))

    # Fetch all results
    rows = cur.fetchall()
    
    # Optionally convert the result to a pandas DataFrame for easier manipulation
    df_a = pd.DataFrame(rows, columns=[desc[0] for desc in cur.description])
    
    df['chicken']=df_a['chicken']
    
    cur.close()
    conn.close()
    df['data'] = pd.to_datetime(df['data'])
    return df

def get_data_with_date(date_value, skip=10):
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
    print(f'\n\nDataframe A:\n {df_a}')


    columns = ['hora', 'paw_a', 'paw_b', 'paw_c', 'chicken']
    columns_str = ', '.join(columns)
    #Read only rows where 'data matches value_date's date and only the columns specified above
    query = f"SELECT {columns_str}  FROM paws WHERE data = '{date_value}'"
    df_p = pd.read_sql_query(query, conn)
    conn.close()
    print(f'\n\nDataframe P:\n {df_p}')

    return df_p, df_a
    #df_p = df_p.sort_values(by=['hora'])
    #df_a = df_a.sort_values(by=['hora']) 
    #return df_p.iloc[::skip], df_a.iloc[::skip]

def compute_chicken_before(df_a):
    tempo_in_out, tempo_in_out_delta = get_tempo_in_out()

    # Convert the 'time' column to datetime.datetime to enable arithmetic
    df_a['time_as_datetime'] = df_a['hora'].apply(lambda t: datetime.combine(datetime.today(), t))
    
    
    last_time = df_a['time_as_datetime'].iloc[-1]
    adjusted_time = last_time - tempo_in_out_delta
    



    # Find the nearest 'time' in the DataFrame
    time_dff = (df_a['time_as_datetime'] - adjusted_time).abs()
    min_time_diff = time_dff.min()

    # Set a tolerance of 1 second
    tolerance = timedelta(seconds=.1)

    # nao houve jeito de fazer esse metodo abaixo funcionar, retorna sempre um valor aleatorio
    nearest_indices = time_dff[time_dff - min_time_diff < tolerance].index
    print(f"\n\nmin_time_diff: {min_time_diff} at index {nearest_indices}")
    #chicken_before1 = df_a['chicken'].iloc[nearest_indices[0]]
    if len(df_a) > 2*(40+4*60):
        chicken_before = df_a['chicken'].iloc[-40-4*60]
    else:
        chicken_before = 0

    #print('\n\n last recorded time: ')
    #print(last_time, len(df_a))
    #print('ago : ')
    #print(df_a['time_as_datetime'].iloc[-40-4*60], nearest_indices[0])
    #print('\n\nchicken: '+str(df_a['chicken'].iloc[-1]))
    #print('chicken_before: '+str(chicken_before)+'\n\n')
    #print('chicken_before1: '+str(chicken_before1)+'\n\n')    
    return chicken_before

def get_data_display(df_p, df_a):
    #TD = update_today()
    if df_p.empty or df_a.empty:
        a = 0
        b = 0
        c = 0
        total = 0
        p_lost = 0
    else:
        total_in = df_a['chicken']
        total_out = df_p['chicken']        
        a = df_p['paw_a']
        b = df_p['paw_b']
        c = df_p['paw_c']
        #chicken_before = compute_chicken_before(df_a)
        #print(f" chicken before: {2*chicken_before}")
        #print(f" (a+b+c): {(a+b+c)}")
        #p_lost = 2 * chicken_before - (a+b+c)
        #print(f" patas lost: {p_lost}")
        #if p_lost < 0:
        #    p_lost = 0
            
    return total_in, total_out, a,b,c  

####################### fnc da aba dias[fim] 

####################### fnc da aba historico
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

def timestamp_to_str(time_as_stamp):
    #timestamp = int(time_as_stamp * 86400)
    print(type(time_as_stamp))
    if type(time_as_stamp) == str:
        timestamp = datetime.strptime(time_as_stamp, '%H:%M')
    else:
        timestamp = datetime(1899, 12, 30) + timedelta(time_as_stamp)
    date_time = timestamp + timedelta(hours=3)
    #print('\n\n*** em tab_functions.timestamp_to_str ***\n\n')    
    #print(f'time_as_stamp: {time_as_stamp} date_time: {date_time}')
    return date_time.strftime('%H:%M:%S')

def get_resumo_range(start_date, end_date):
    conn = psycopg2.connect(database="mytestdb",
                            user="postgres",
                            host='localhost',
                            password="theia@24",
                            port=5432)
    
    query = f"SELECT * FROM Integrados WHERE date >= '{start_date}' AND date <= '{end_date}'"
    df = pd.read_sql_query(query, conn)
    conn.close()
    #print(f'\nData frame em get_resumo_range {df}')
    # Aggregate by 'name'
    aggregated_df = df.groupby('name').agg({
        'chicken': 'sum',
        'paw_a': 'sum',
        'paw_b': 'sum',
        'paw_c': 'sum'
    }).reset_index()

    aggregated_df['Nota'] = round(3 * aggregated_df['paw_a'] / (aggregated_df['paw_a']+aggregated_df['paw_b']+aggregated_df['paw_c']) + 7 * (
                1 - aggregated_df['paw_c'] / (aggregated_df['paw_a']+aggregated_df['paw_b']+aggregated_df['paw_c'])), 2)

    #print(f'Resumo range: {aggregated_df}')
    
    return aggregated_df
####################### funções historico[fim]

####################### funções aba upload
def time_to_seconds(t):
    return t.hour * 3600 + t.minute * 60 + t.second

def get_previsao_carga(excel_path):
    print('\n\n\n *** tab_functions.get_previsao_carga***')
    # carrega arquivo agrosys
    if excel_path.endswith('.xlsb'):
        df_carga = pd.read_excel(excel_path, engine='pyxlsb')
    else:
        df_carga = pd.read_excel(excel_path)

    indices = df_carga.apply(lambda row: row.astype(str).str.contains('Placa', case=False, na=False)).any(axis=1)

    # Get the indices where the condition is True
    placa_indices = df_carga[indices].index.to_list()
    #print(f'placa_indices: {placa_indices}')
    #columns = ['Unnamed: 0', 'Unnamed: 2', 'Unnamed: 13', 'Unnamed: 22', 'Unnamed: 25']
    columns = ['Data', 'Granja', 'Unnamed: 13', 'Unnamed: 22', 'Unnamed: 25']
    rows = []
    Integrado = []
    Lote = []
    j = 0
    #print(f'\n df_carga:\n {df_carga}')
    for ii in placa_indices:  # how many cells with string 'placas' are there
        j = j + 1
        for i in range(ii+1, len(df_carga)):  # three cells down (ii+3) we start to see the plate numbers
            if isinstance(df_carga['Data'].iloc[i], str) and len(df_carga['Data'].iloc[i]) == 7:
                rows.append(i)  # add if it looks like a plate
                Integrado.append(df_carga['Até'].iloc[ii - 2])
                Lote.append(j)
            else:
                break  # go to next produtor

    #print(f'\n\nIntegrados: {Integrado}\n\n')
    #print(f'\n\nLote: {Lote}\n\n')
    df_prev_cargas = df_carga.loc[rows, columns]
    df_prev_cargas.columns = ['Placa', 'Lote', 'Inicio do Abate', 'Aves na Carga', 'Aves Mortas']
    print(f'\n\n df_prev_cargas 1:\n{df_prev_cargas}\n\n')
    

    df_prev_cargas['Inicio do Abate'] = df_prev_cargas['Inicio do Abate'].apply(lambda x: timestamp_to_str(x))
    print(f'\n\n df_prev_cargas 2:\n{df_prev_cargas}\n\n')
    df_prev_cargas['Inicio do Abate'] = pd.to_datetime(df_prev_cargas['Inicio do Abate'], format='%H:%M:%S') - timedelta(hours=4)
    print(f'\n\n df_prev_cargas 3:\n{df_prev_cargas}\n\n')
    df_prev_cargas['Inicio do Abate'] = df_prev_cargas['Inicio do Abate'].dt.time

    df_prev_cargas.reset_index(drop=True, inplace=True)

    df_prev_cargas = df_prev_cargas.assign(Integrado=pd.Series(Integrado).values)
    df_prev_cargas = df_prev_cargas.assign(Lote=pd.Series(Lote).values)
    df_prev_cargas['Total de aves'] = df_prev_cargas['Aves na Carga']# - df_prev_cargas['Aves Mortas']

    print(f'\n\n df_prev_cargas END:\n{df_prev_cargas}\n\n')
    
    print('--- fim tab_functions.get_previsao_carga***')
    return df_prev_cargas

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
    print(f'\n dados coletados para o dia {date_value}')
    print(df_p['hora'].iloc[100:120])    
    return df_a, df_p, df_carga

def create_resumo(date_value):
    ''' This function recevies the date to compute resumo from the excel file and the data set
    '''
    print('\n\n *** tab_functions.create_resumo ***\n\n')
    tempo_in_out, tempo_in_out_delta = get_tempo_in_out()
    df_a, df_p, df_carga = get_df_a_p_carga(date_value)

    print(f' \n Dataframe carga:\n {df_carga}')
    
    if df_p.empty:
        print('\n\ndf_p.empty\n\n')
        return pd.DataFrame([]), False, False
    if df_carga.empty:
        print('\n\ndf_carga.empty\n\n')
        return pd.DataFrame([]), True, False

    # Sort values by 'hora' in place
    df_p.sort_values(by=['hora'], inplace=True)
    # Reset the index and drop the old index to avoid it being added as a column
    df_p.reset_index(drop=True, inplace=True)
    #print(df_p['hora'].iloc[100:120])    


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
    # Aggregating the values of 'chicken' in df_p, keeping the first occurrence of each 'hora'
    df_p_aggregated = df_p.groupby('hora')['chicken'].first()

    # Ensure that the result is a unique Series and set the index explicitly
    df_p_aggregated = pd.Series(df_p_aggregated)
    

    

    # AJUSTES DE df_a
    #df_a['hora'] = pd.to_datetime(df_a['hora'], format='%H:%M:%S').dt.time
    #t_zero = df_a['hora'].iloc[0].hour * 3600 + df_a['hora'].iloc[0].minute * 60 + df_a['hora'].iloc[
    #    0].second
    #df_a['Tempo'] = df_a['hora'].apply(time_to_seconds) - t_zero
    
    # copies chicken in df_p to df_a at the correct time slots    
    #df_a['chicken out'] = df_a['hora'].map(df_p_aggregated)
    
    # now a copy shifted by time    
    # Aggregate the shifted values, ensuring uniqueness
    #df_p_shifted_aggregated = df_p.groupby('hora_shifted')['chicken'].last()
    # Map the shifted 'Frango' values to 'chicken shifted' in df_a
    #df_a['chicken shifted'] = df_a['hora'].map(df_p_shifted_aggregated)
    
    #agora a diferenca entre in e out
    #df_a['dif'] = df_a['chicken']-df_a['chicken out']
    #df_a['dif shifted'] = df_a['chicken']-df_a['chicken shifted']

    #df_a['dchicken'] = (df_a['chicken'].shift(10) - df_a['chicken'].shift(-10)) / (
    #        df_a['Tempo'].shift(10) - df_a['Tempo'].shift(-10))    
    #df_a['dchicken out'] = (df_a['chicken out'].shift(10) - df_a['chicken out'].shift(-10)) / (
    #        df_a['Tempo'].shift(10) - df_a['Tempo'].shift(-10))
    #df_a['dchicken shifted'] = (df_a['chicken shifted'].shift(10) - df_a['chicken shifted'].shift(-10)) / (
    #        df_a['Tempo'].shift(10) - df_a['Tempo'].shift(-10))
    #df_a['ddif shifted'] = (df_a['dif shifted'].shift(10) - df_a['dif shifted'].shift(-10)) / (
    #        df_a['Tempo'].shift(10) - df_a['Tempo'].shift(-10))   
    #df_a['Indicador de Dif Elevada'] = df_a['ddif shifted'].apply(lambda x: 1 if x > 1 else 0)   
    #df_a['Indicador de Parada'] = df_a['ddif shifted'].apply(lambda x: 1 if x == 0 else 0)  
             
    #indice_trecho_final = round(len(df_a)*11/12)
    




    #  RELATÓRIO DE CARGAS...
    # Find the index where the word 'placa' exists in the DataFrame
    indices = df_carga.apply(lambda row: row.astype(str).str.contains('Placa', case=False, na=False)).any(axis=1)

    # Get the indices where the condition is True
    placa_indices = df_carga[indices].index.to_list()
    columns = ['Data', 'Granja', 'Unnamed: 13', 'Unnamed: 22', 'Unnamed: 25']
    rows = []
    Integrado = []
    Lote = []
    j = 0
    for ii in placa_indices:  # how many cells with string 'placas' are there
        j = j + 1
        for i in range(ii + 1, len(df_carga)):  # three cells down (ii+3) we start to see the plate numbers
            if isinstance(df_carga['Data'].iloc[i], str) and len(df_carga['Data'].iloc[i]) == 7:
                rows.append(i)  # add if it looks like a plate
                Integrado.append(df_carga['Granja'].iloc[ii - 1])
                Lote.append(j)
            else:
                break  # go to next produtor

    # planilha interpretação do relatorio
    excel_path = 'uploads/'+date_value+'.xlsb'
    df_prev_cargas = get_previsao_carga(excel_path)
    df_prev_cargas_time_sorted = df_prev_cargas.sort_values(by='Inicio do Abate')

    print('\n\n previsão de cargas:')
    print(df_prev_cargas_time_sorted)

    # tabela total acumulado em ordem cronológica
    total_contagem = df_p['chicken'].iloc[-1]
    total_estimado = df_prev_cargas['Total de aves'].sum()
    discrepancia = total_contagem / total_estimado
    
    print('\n\n total contagem')
    print(total_contagem)
    print('\n\n total estimado')
    print(total_estimado)
    print('\n\n Discrepancia')
    print(discrepancia)
    print('\n\n')

    # df_acumulado['Lote'] = df_prev_cargas['Lote']
    data = [df_prev_cargas_time_sorted['Lote'].astype(int), (df_prev_cargas['Total de aves'] * discrepancia)]
    df_acumulado = pd.DataFrame(data)
    df_acumulado = df_acumulado.T
    df_acumulado.columns = ['Lote', 'chicken Ajustados']
    df_acumulado['Acumulado'] = df_acumulado['chicken Ajustados'].cumsum().astype(int)
    df_acumulado['chicken Ajustados'] = df_acumulado['chicken Ajustados'].astype(int)

    print('\n\n df accu:')
    print(df_acumulado)
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
            print(index)
            index = df_p['Indicador de Intervalo'][interv[0]:interv[1]].idxmax()
            print(index)

            
        print(df_p['chicken'].iloc[index])
        print(df_acumulado['Acumulado'].iloc[i])
        print(f'no index {index}\n \n')
        # print(index, int(df_p['chicken'].iloc[index]), int(df_p['paw_a'].iloc[index]))
        data_acc_ajustada.append([int(df_acumulado['Lote'].iloc[i]),
                                  int(df_p['chicken'].iloc[index]),  # qtd de chicken
                                  int(df_p['paw_a'].iloc[index]),  # Patas A
                                  int(df_p['paw_b'].iloc[index]),  # Patas B
                                  int(df_p['paw_c'].iloc[index]),  # Patas C
                                  df_p['hora'].iloc[index]
                                  ])

    
    
    # Print the DataFrame
    print("\n\n data acc ajustada:")
    print(pd.DataFrame(data_acc_ajustada))
    
    d = data_acc_ajustada
    data_por_carga = [d[0][:]]

    for i in range(len(data_acc_ajustada) - 1):
        data_por_carga.append(
            [d[i + 1][0], d[i + 1][1] - d[i][1], d[i + 1][2] - d[i][2], d[i + 1][3] - d[i][3], d[i + 1][4] - d[i][4]])

    df_por_carga = pd.DataFrame(data_por_carga)
    df_por_carga.columns = ['Lote', 'chicken', 'paw_a', 'paw_b', 'paw_c', 'hora']
    
    print("\n\n df por carga:")
    print(df_por_carga)

    data_datetime = pd.to_datetime(df_carga['Data'].iloc[0], origin='1899-12-30', unit='D')

    # tabela resumo do dia
    unidade_id = get_unidade_id()
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
    print('\n\n --- fim tab_functions.create_resumo ---\n\n')
    return df_resumo, True, True



######################## funções aba upload [fim]














if __name__ == "__main__":
    # Get the disabled days
    table_name = 'paws'
    zero_column= 'paw_b'
    date_column= 'data'
    disabled_days, st_day, end_day = get_date_picker_days(table_name, zero_column, date_column)
    print(f'\nas datas one a coluna {zero_column} não possui dados na tabela {table_name} são:')
    for i in range(len(disabled_days)):
        print(disabled_days[i])    
    print(f'\ndata de inicio: {st_day}\ndata de fim: {end_day}\n\n')


    


    TD, YY, MM, DD, CT = update_today()

    df_past_days = get_days_range()

    print(df_past_days)
    
    df_p, df_a = get_data_with_date(TD)
    get_data_display(df_p, df_a)
    df_a = compute_chicken_before(df_a)



