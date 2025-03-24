'''nessa v2 foram adicionados os comentarios do Gelson: 
1) Ali na aba Histórico, colocar as contagens totais de Frango, Patas, Perdidos e Aves Mortas
2) Também no histórico, mostrar o valor de frangos perdidos e aves mortas em percentuais
3) poder consultar um único dia no histórico
4) mostrar resultados do dia mesmo que não tenha ainda os resultados dos integrados
'''



import dash
from dash import dcc, html, Dash, dash_table, State
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from flask import Flask
import pandas as pd
import psycopg2
from datetime import date, timedelta, datetime, time
import plotly.graph_objs as go
import numpy as np


if __name__ == '__main__': 
    import tab_functions
else:    
    from tabs import tab_functions 

blacklist_dates = tab_functions.get_blacklist_dates()
disabled_dates = [date.fromisoformat(d) for d in blacklist_dates]
TD, YY, MM, DD, CT = tab_functions.update_today()

print(f'\n\nToday is {YY} - {MM} - {DD}\n')

def generate_dates_list(start_date, end_date):
    blacklist_dates = tab_functions.get_blacklist_dates()
    date_list = []
    current_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    while current_date <= end_date:
        if current_date.strftime("%Y-%m-%d") not in blacklist_dates:            
            date_list.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)
    #print(f'Dates to retrieve {date_list}')
    return date_list

def fetch_last_rows(date_to_see, row_limit=10000):
    try:
        conn = psycopg2.connect(
            database="mytestdb",
            user="postgres",
            host='localhost',
            password="theia@24",
            port=5432)
        
        query = f"SELECT hora, chicken, paw_a, paw_b, paw_c  FROM paws WHERE data = '{date_to_see}' ORDER BY hora ASC"
        df_p = pd.read_sql_query(query, conn)
        query = f"SELECT hora, chicken FROM animals WHERE data = '{date_to_see}' ORDER BY hora ASC"
        df_a = pd.read_sql_query(query, conn)
        
        return df_a.tail(row_limit), df_p.tail(row_limit)

    except Exception as e:
        print(f"An error occurred: {e}")
        return []

    finally:
        #cur.close()
        conn.close()

def insert_data_into_table(cursor, conn, data):
    cursor.execute('''
        INSERT INTO resumo_dia (date, empresa_id, frangos_entrada, frangos_mortos, 
                                frangos_perdidos, patas_A, patas_B, patas_C)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ''', (data['date'], data['empresa_id'], data['frangos_entrada'], data['frangos_mortos'], 
          data['frangos_perdidos'], data['patas_A'], data['patas_B'], data['patas_C']))
    conn.commit()
    print(f"Data for {data['date']} inserted into 'resumo_dia' table.")

def compute_data_for_date(date): 
    df_a, df_p = fetch_last_rows(date)
    if not df_a.empty and not df_p.empty:
        df_a = df_a.drop_duplicates(subset='hora', keep='first')
        df_p = df_p.drop_duplicates(subset='hora', keep='first')
        df = df_a
        
        df['hora'] = pd.to_datetime(df['hora'], format='%H:%M:%S')
        df['hora_in_seconds'] = (df['hora'] - df['hora'].iloc[0]).dt.total_seconds()

        
        # Ensure 'chicken' and 'hora_in_seconds' are in numeric format
        df['chicken_derivative'] = np.gradient(df['chicken'], df['hora_in_seconds'])
        # Define the window size for moving average (e.g., 5)
        window_size = 10
        # Apply a moving average to smooth the 'chicken_derivative' column
        df['chicken_derivative_smoothed'] = df['chicken_derivative'].rolling(window=window_size, center=True).mean()
        df['chicken_derivative_smoothed'] = df['chicken_derivative_smoothed']/df['chicken_derivative_smoothed'].max()
        reversed_derivative = df['chicken_derivative_smoothed'][::-1]
        
        not_zero  = 0
        for i, value in enumerate(reversed_derivative):
            if value != 0:
                not_zero += 1
                if not_zero > 50:
                    break
            else: 
                not_zero = 0

        print(f'\n(Compute loss):\nInicio da derivada diferente de zero em i={i}')
        # Step 2: Now search for the first interval of 100 consecutive zeros after encountering the first non-zero
        if not_zero:
            # Initialize variables for finding the interval of 100 consecutive zeros
            zero_interval_start = None
            consecutive_zero_count = 0

            for j in range(i, len(reversed_derivative)):
                if reversed_derivative.iloc[j] < 0.1:
                    if zero_interval_start is None:
                        zero_interval_start = j                    
                    consecutive_zero_count += 1
                    
                    if consecutive_zero_count == 120:
                        # We've found the first interval of 100 consecutive zeros
                        interval_indices = (zero_interval_start, j)
                        break
                else:
                    #print(reversed_derivative.iloc[j])
                    # Reset if we encounter a non-zero
                    zero_interval_start = None
                    consecutive_zero_count = 0
                    interval_indices = (0, 0)
        



        start = len(reversed_derivative)-interval_indices[1]
        end = len(reversed_derivative)-interval_indices[0]

        i_total = (start+end) // 2
        
        if i_total == 3600:
            print('problemas com indices')
        else: 
            frangos_in = df['chicken'].iloc[-1]
            frangos_m = max(frangos_in-df['chicken'].iloc[i_total],0)
            frangos_perd = max(df['chicken'].iloc[i_total] - df_p['chicken'].iloc[-1],0)
            PA = df_p['paw_a'].iloc[-1]
            PB = df_p['paw_b'].iloc[-1]
            PC = df_p['paw_c'].iloc[-1]
    else:
        frangos_in = 0
        frangos_m = 0
        frangos_perd = 0
        PA = 0
        PB = 0
        PC = 0
        print('Sem dados para calcular as perdas')
    
    print(f'computed data is:\n{date} as type {type(date)}\n{frangos_in} as type {type(frangos_in)}\n{frangos_m} as type {type(frangos_m)}\n{PA} as type {type(PA)}')
    return {
        'date': date,
        'empresa_id': 1,
        'frangos_entrada': int(frangos_in),
        'frangos_mortos': int(frangos_m),
        'frangos_perdidos': int(frangos_perd),
        'patas_A': int(PA),
        'patas_B': int(PB),
        'patas_C': int(PC)
    }

# Function to retrieve data from the 'resumo_dia' table and handle missing data
def retrieve_data(dates_to_retrieve):
    try:
        # Connect to the database
        conn = psycopg2.connect(
            database="mytestdb",
            user="postgres",
            host='localhost',
            password="theia@24",
            port=5432)
        
        # Create a cursor object and a DataFrame for the results
        cursor = conn.cursor()
        resumo_df = pd.DataFrame()

        for date in dates_to_retrieve:
            cursor.execute("SELECT * FROM resumo_dia WHERE date = %s", (date,))
            rows = cursor.fetchall()


            # If data is found, append it to the DataFrame
            if rows:
                print(f'Found data for date = {date}:')
                print(f'\nThis is the row found:\n {rows}\n\n')

                columns = [desc[0] for desc in cursor.description]
                temp_df = pd.DataFrame(rows, columns=columns)
                print(f'Adding row {temp_df}')
                resumo_df = pd.concat([resumo_df, temp_df], ignore_index=True)

            else:
                # If no data found, call a function to compute and insert data
                print(f'No data found for date = {date}, checking if there is data...')
                #cursor.execute("SELECT hora FROM animals WHERE data = %s", (date,))
                cursor.execute("SELECT MAX(hora) FROM animals WHERE data = %s", (date,))
                last_entry = cursor.fetchall()
                last_entry = last_entry[0][0]
                print(f'\n\n {last_entry}')                    
                print(f'Last entry for {date} at time {last_entry}')
                if last_entry:
                    min_time = time(15, 30, 0)                
                    if last_entry > min_time:
                        computed_data = compute_data_for_date(date)
                        print('   ...adding to the table...')
                        print(type(computed_data))
                        insert_data_into_table(cursor, conn, computed_data)
                        print('.. data added, building dataframe... ')
                        resumo_df = pd.concat([resumo_df, pd.DataFrame([computed_data])], ignore_index=True)
                        print('... done.')
                print('\n\nRESUMO_DF retrieved:\n')
            print(resumo_df)
        print("Data retrieval and/or insertion complete.")
        
    except (Exception, psycopg2.DatabaseError) as error:
        print("Error while retrieving data:", error)
    finally:
        # Close cursor and connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return resumo_df


def historico_table(start_date, end_date, PF, VF, PP, VA, VB, VC, USS):
    dates_to_retrieve = generate_dates_list(start_date, end_date)
    print(f'\n dates_to_retrieve em historico_table as type {type(dates_to_retrieve)}: \n {dates_to_retrieve}\n\n')
    df = retrieve_data(dates_to_retrieve)
    
    print(f'\nData frame em historico\n {df}\n\n')
    
    #  Filter out rows where the 'date' is in the blacklist
    #df['date'] = df['date'].astype(str)
    table = []
    #print('\n\ncriando tabela\n\n')
    if not df.empty:                
        df_display = df.drop(columns=['empresa_id'])
        df_display.columns = ['Data', 'Frangos', 'Mortos na Entradas', 'Perdidos no Processo', 'Patas A', 'Patas B', 'Patas C',  ]
        df_display['Ganhos Patas'] = (PP*VA*df_display['Patas A']+PP*VB*df_display['Patas B'])*USS
        df_display['Perdas Processo'] = (-VF*PF*(df_display['Perdidos no Processo']))
        df_display['Perdas Mortos'] = (-VF*PF*df_display['Mortos na Entradas'])
        df_display['Perdas C'] = (USS*VC*PP*df_display['Patas C'])
        df_display['Perdas'] = (-VF*PF*(df_display['Perdidos no Processo']+df_display['Mortos na Entradas']) + USS*VC*PP*df_display['Patas C'])
        # Create a new row with the label "Totais" in the first cell and sums in the remaining cells
        totals_row = pd.DataFrame([['Totais'] + df_display.sum(numeric_only=True).tolist()], columns=df_display.columns)
        df_display['Perdidos no Processo'] = df_display.apply(
            lambda row: f"{row['Perdidos no Processo']} ({(row['Perdidos no Processo'] / row['Frangos'] * 100):.1f}%)"
            if row['Frangos'] != 0 else f"{row['Perdidos no Processo']} (N/A)",
            axis=1)

        df_display['Mortos na Entradas'] = df_display.apply(
            lambda row: f"{row['Mortos na Entradas']} ({(row['Mortos na Entradas'] / row['Frangos'] * 100):.1f}%)"
            if  row['Frangos']!= 0 else f"{row['Mortos na Entradas']} (N/A)",
            axis=1)
        # Append the new row to the original DataFrame
        df_display = pd.concat([df_display, totals_row], ignore_index=True)
        df_display['Ganhos Patas'] = df_display['Ganhos Patas'].apply(lambda x: f"R${x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        df_display['Perdas Processo'] = df_display['Perdas Processo'].apply(lambda x: f"R${x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        df_display['Perdas Mortos'] = df_display['Perdas Mortos'].apply(lambda x: f"R${x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        df_display['Perdas C'] = df_display['Perdas C'].apply(lambda x: f"R${x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        df_display['Perdas'] = df_display['Perdas'].apply(lambda x: f"R${x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        
        selected_columns = ['Data','Frangos','Perdidos no Processo','Mortos na Entradas','Patas A','Patas B','Patas C', 'Perdas']
        
        columns = [
            {"name": [" ","Data"], "id": "Data"},
            {"name": ["Frangos", "Entrada"], "id": "Frangos"},
            {"name": ["Frangos","Perdidos no Processo"], "id": "Perdidos no Processo"},
            {"name": ["Frangos","Mortos na Entradas"], "id": "Mortos na Entradas"},
            {"name": ["Patas", "A"], "id": "Patas A"},
            {"name": ["Patas", "B"], "id": "Patas B"},
            {"name": ["Patas", "C"], "id": "Patas C"},
            {"name": ["Perdas", "Processo"], "id": "Perdas Processo"},
            {"name": ["Perdas", "Mortos"], "id": "Perdas Mortos"},
            {"name": ["Perdas", "Patas C"], "id": "Perdas C"},
            {"name": ["Perdas", "Totais"], "id": "Perdas"}
        ]
        
        df_display = df_display[df_display['Frangos'] != 0]
        table = dash_table.DataTable(
            data=df_display.to_dict('records'),
            columns=columns,
            merge_duplicate_headers=True,  # Enable header merging
            page_size=len(df_display.index),  # Adjust the page size as needed
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '5px'},
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)',
                'fontWeight': 'bold'
                },
            style_data_conditional=[
                    {
                        'if': {'row_index': len(df_display)-1},  # Apply to the last row
                        'fontWeight': 'bold'  # Set the font weight to bold
                    }
                ],
            export_format="xlsx",
            )

    return table, df

def define_bar_layout_vertical():
    return go.Layout(barmode='group',
                     title={'text': 'Desempenho no período'},
                     yaxis=dict(automargin=True, ticksuffix="  "),
                     xaxis={'tickangle': 0, 'tickfont': {'size': 14}},
                     font_family=tab_functions.font_family,
                     font={'size': 20},
                     hoverlabel=dict(
                         font_size=20,
                         font_family=tab_functions.font_family)
                     )

def define_bar_layout():
    return go.Layout(barmode='stack',
                     title={'text': 'Integrado e Nota', 'x': 0.05},
                     yaxis=dict(automargin=True, 
                                ticklabelposition="inside right", 
                                autorange='reversed', 
                                ticksuffix="  ",
                                tickmode="array"),
                     xaxis={'tickangle': 0, 'tickfont': {'size': 14}},
                     font_family=tab_functions.font_family,
                     font={'size': 20},
                     hoverlabel=dict(
                         font_size=20,
                         font_family=tab_functions.font_family)
                    )

def define_bar_layout_v():
    return go.Layout(barmode='group',
                     title={'text': 'Desempenho do período'},
                     yaxis=dict(automargin=True, ticksuffix="  "),
                     xaxis={'tickangle': 0, 'tickfont': {'size': 14}},
                     font_family=tab_functions.font_family,
                     font={'size': 20},
                     hoverlabel=dict(
                         font_size=20,
                         font_family=tab_functions.font_family)
                     )

####################### layout defs [fim]


bar_layout_v = define_bar_layout_v()


bar_layout = define_bar_layout()


# Dia Tab Layout
layout = dbc.Card([
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
                        minimum_nights=0,
                        disabled_days=disabled_dates,
                        #end_date=date(YY, MM, DD)
                    ),),
                ], xs=12, sm=12, md=4, lg=3, xl=3),                   
            ], justify="start"),
                        
            dbc.Row(html.Div(id='historico-text')),
            html.Hr(),
            dbc.Row([
                dbc.Card(id='table-historico-geral', body=True, outline=False, style={'border': 'none'}), 
            ]),
            dbc.Row([
                dbc.Row(dcc.Graph(id='Historico_v', style={'display': 'none'})),
            ]),
            html.Hr(),
            dbc.Row(html.H5("Mostrar dados dos Integrados ordenados por:")),
                    dbc.Row(dcc.RadioItems(["ordem alfabética", "volume", "nota"],
                                            id='historico-ordem',
                                            style={'font-size': 18},
                                            inputStyle={"margin-right": "20px"})),
            dbc.Row(dcc.Graph(id='historico-plot', style={'display': 'none'})),
            #dbc.Row(dcc.Graph(id='integrado-plot', style={'margin-right': '100px', 'border': '0px black solid', 'display': 'none'})),    
        ], body=True, outline=False, id='capture-card-historico')# fim da aba 'historico'


# Callback tab 'financeiro'
def register_callbacks(dash_app):
    @dash_app.callback(
        Output('historico-text', 'children'),
        Output("Historico_v","figure"),
        Output("Historico_v","style"),
        Output('table-historico-geral','children'),
        
        Input("historico-intervalo", "start_date"), 
        Input("historico-intervalo", "end_date"),
        Input("peso-F", 'value'),
        Input("valor-F", 'value'),
        Input("peso-P", 'value'),
        Input("dolar-A", 'value'),
        Input("dolar-B", 'value'),
        Input("dolar-C", 'value'),
        Input("conv", 'value'),
    )
    def atualiza_historico(start_date, end_date, PF, VF, PP, VA, VB, VC, USS):
        table = []
        if start_date is None or end_date is None:
            return {}, {}, {'display': 'none'}, table#{}, {'display': 'none'}, table
        
        table, df = historico_table(start_date, end_date, PF, VF, PP, VA, VB, VC, USS)
        print(f'\n\Data frame da aba historico: \n{df}')
        if df.empty:
            return html.H5('Sem dados no período: tabela resumo vazia'), {}, {'display': 'none'}, []
                #                               [], figure_v, style_v, figure, []
        else:

            #df_last_days = tab_functions.get_days_range(start_date, end_date)

            # bor plot of different dates, based on df_last_days data frame
            trace_A = go.Bar(y=df['patas_a'], x=df['date'],
                             name='Patas A', marker={'color': tab_functions.colors['paw_a']},
                             showlegend=False)
            trace_B = go.Bar(y=df['patas_b'], x=df['date'],
                             name='Patas B', marker={'color': tab_functions.colors['paw_b']},
                             showlegend=False)
            trace_C = go.Bar(y=df['patas_c'], x=df['date'],
                             name='Patas C', marker={'color': tab_functions.colors['paw_c']},
                             showlegend=False)
            style_v = {'margin-bottom': '10px',
                        'margin-top': '10px',
                        'margin-left': '30px',
                        'margin-right': '20px',
                        'height': 500,
                        'width': '100%',
                        'border': '0px gray solid',
                        'borderRadius': '15px',
                        'ticksuffix': "  "
                        }
            data_dias = [trace_A, trace_B, trace_C]


            figure_v = {'data': data_dias, 'layout': bar_layout_v}


        


        

        return [], figure_v, style_v, table#figure, style, table

    @dash_app.callback(            
        Output("historico-plot", "figure"),
        Output("historico-plot", "style"),
        Input('historico-ordem', 'value'),  # seletor de ordenamento
        State('historico-intervalo', 'start_date'),  # Access start_date as State
        State('historico-intervalo', 'end_date')     # Access end_date as State
    )
    def atualiza_ordem(ordem,start_date, end_date):
        if start_date is None or end_date is None:
            return {}, {'display': 'none'}
        df = tab_functions.get_resumo_range(start_date, end_date)
        print('\n\n')
        print(df)
        print('\n\n')
        print(df.columns)
        if df.empty:
            return  {}, {'display': 'none'}
                #                               [], figure_v, style_v, figure, []
        else:
            
            if ordem == 'ordem alfabética':
                df_aux = df.sort_values(by=['name'])
            if ordem == 'nota':
                df_aux = df.sort_values(by=['Nota'], ascending=False)
            if ordem == 'volume':
                df_aux = df.sort_values(by=['chicken'], ascending=False)
            
            max_length = df_aux['name'].str.len().max()
            df_aux['padded_name'] = df_aux['name'].str.pad(width=max_length, side='right')

            trace_A = go.Bar(y=df_aux['padded_name'] + ':  ' + df_aux['Nota'].astype(str), x=df_aux['paw_a'],
                            name='Patas A', marker={'color': tab_functions.colors['paw_a']}, width=.4, orientation='h')
            trace_B = go.Bar(y=df_aux['padded_name'] + ':  ' + df_aux['Nota'].astype(str), x=df_aux['paw_b'],
                            name='Patas B', marker={'color': tab_functions.colors['paw_b']}, width=.4, orientation='h')
            trace_C = go.Bar(y=df_aux['padded_name'] + ':  ' + df_aux['Nota'].astype(str), x=df_aux['paw_c'],
                            name='Patas C', marker={'color': tab_functions.colors['paw_c']}, width=.4, orientation='h')
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
        return figure, style


if __name__ == '__main__':   
    print('\n\nrunning locally\n\n')
    app = Flask(__name__)
    dash_app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY, '/assests/styles.css'], 
                    url_base_pathname='/', 
                    server=app)
    dash_app.title = 'THEIA - historico'
    dash_app.layout = layout
    register_callbacks(dash_app)  # Register the callback with the local app
    dash_app.run_server(debug=True)