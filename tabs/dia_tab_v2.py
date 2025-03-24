
from dash import dcc, html, Dash, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from flask import Flask
import dash_player as dp
import plotly.graph_objs as go
import time
import pandas as pd
from datetime import datetime, date
import glob
import os
import requests

if __name__ == '__main__': 
    import tab_functions
else:    
    from tabs import tab_functions 
global TD, YY, MM, DD, CT 
TD, YY, MM, DD, CT = tab_functions.update_today()

dis_day_paws, st_day_paws, end_day_paws = tab_functions.get_date_picker_days('paws', 'chicken', 'data')

blacklist_dates = tab_functions.get_blacklist_dates()
disabled_dates = [date.fromisoformat(d) for d in blacklist_dates]

#Total, A, B, C = tab_functions.get_data_display(df_p, df_a)
paws_lost = 0
Total_in = 0
Total_out = 0
A = 0
B = 0
C = 0

def compute_display_data(df):
    # Convert 'hora' to datetime
    df['hora'] = pd.to_datetime(df['hora'], format='%H:%M:%S')
    
    # Truncate 'hora' to only include the hour and minute (eliminate seconds)
    df['hora'] = df['hora'].dt.floor('min')  # 'min' stands for minute
    
    # Aggregate the data by minute and compute the mean 'chicken' values for each minute
    df_minute = df.groupby('hora', as_index=False)['chicken'].mean()

    # Create a complete range of minutes from the min to max 'hora'
    full_minute_range = pd.date_range(start=df_minute['hora'].min(), end=df_minute['hora'].max(), freq='min')

    # Reindex the dataframe to this new minute range
    df_full = df_minute.set_index('hora').reindex(full_minute_range)

    # Interpolate the missing 'chicken' values using linear interpolation
    df_full['chicken'] = df_full['chicken'].interpolate()

    # Reset index so that 'hora' becomes a column again
    df_full.reset_index(inplace=True)
    df_full.rename(columns={'index': 'hora'}, inplace=True)

    # Format 'hora' to display only the hour and minute
    df_full['hora'] = df_full['hora'].dt.strftime('%H:%M')

    # Final dataframe with missing times filled and 'chicken' values interpolated
    return df_full['hora'], df_full['chicken']



def delete_older_videos():
    # Path to your folder
    folder_path = '/var/www/html/stream/hls/'

    # Get all .pt files in the directory
    files = glob.glob(os.path.join(folder_path, '*.ts'))

    # Ensure there are .pt files in the directory
    if len(files)  > 3:
        # Sort files by modification time, the most recent files will be at the end
        files.sort(key=os.path.getmtime)

        # Keep the last three most recent files
        most_recent_files = files[-3:]

        # Delete all other .pt files
        for file in files[:-3]:
            os.remove(file)
            print(f"Deleted {file}")

        print(f"Most recent .pt files {most_recent_files} were not deleted.")
    else:
        print("Not enough .pt files to delete. Only three or fewer files in the directory.")


def define_line_trace(x, y, name = 'dados', color='royalblue', width=2):
    return go.Scatter(x=x, y=y, mode='lines', line=dict(color=color, width=width), name = name)


def define_total_frangos_layout(dtick):
    return go.Layout(title='Frangos',
                     xaxis={'title': 'Horário', 'tickangle': 0, 'dtick': dtick},
                     hoverlabel=dict(
                         font_size=20,
                         font_family=tab_functions.font_family),
                     )


def define_pie_trace(val, labe):
    return go.Pie(values=val, labels=labe,
                  textinfo='label+percent',
                  # textfont_size=20,
                  sort=False,
                  pull=[0, 0, 0.2],
                  marker=dict(colors=[tab_functions.colors['paw_a'], tab_functions.colors['paw_b'], tab_functions.colors['paw_c']])
                  )


def define_pie_layout():
    return go.Layout(title='Qualidade',
                     legend={'traceorder': 'normal'},
                     hoverlabel=dict(
                         font_size=20,
                         font_family=tab_functions.font_family)
                     )




def define_bar_layout_dia():
    return go.Layout(barmode='group',
                     title={'text': 'Desempenho nos últimos dias'},
                     yaxis=dict(automargin=True, ticksuffix="  "),
                     xaxis={'tickangle': 0, 'tickfont': {'size': 14}},
                     font_family=tab_functions.font_family,
                     font={'size': 20},
                     hoverlabel=dict(
                         font_size=20,
                         font_family=tab_functions.font_family)
                     )

####################### layout defs [fim]


bar_layout_dia = define_bar_layout_dia()

# Dia Tab Layout
layout = dbc.Card([
        dcc.Interval(id='dia-atualiza dados', interval=60000, n_intervals=0),
        dbc.Row([
            dbc.Col(
                dcc.DatePickerSingle(
                month_format='MMM YYYY',
                display_format='DD/MM/2024',    
                id='date-picker-dia',
                min_date_allowed=st_day_paws,
                max_date_allowed=TD,
                initial_visible_month=TD,  # To make sure the calendar starts on a month that has valid dates
                disabled_days=disabled_dates,
                date=TD,
                style={'margin': '20px'}), 
            xs=6, sm=6, md=2, lg=2),
            dbc.Col(
                dbc.Button(children=['Atualizar'], 
                           className="mr-3", 
                           id='atualizar', 
                           n_clicks=0,
                           style={'margin': '25px'}),
            xs=6, sm=6, md=2, lg=2),
        ]),
        dbc.Row([
            dbc.Col(
            dbc.Card(dbc.CardBody([
                html.H5('Frangos Entrada', className='text-title'),
                html.H3(dbc.Badge(Total_in, color='primary', className="me-3", id='dia-badge-total'))]),
            ), xs=6, sm=6, md=2, lg=2
            ),
            dbc.Col(
            dbc.Card(dbc.CardBody([
                html.H5('Frangos Saída', className='text-title'),
                html.H3(dbc.Badge(Total_out, color='blue', className="me-3", id='dia-badge-patas'))]),
            ),xs=6, sm=6, md=2, lg=2
            ),
            dbc.Col(
            dbc.Card(dbc.CardBody([
                html.H5('Frangos Perdidos ', className='text-title'),
                html.H3(dbc.Badge(Total_in - Total_out, color='danger', className="me-3",
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
            dbc.Col(dcc.Graph(id='dia-Frango Total', style={'display': 'none'}),
                            xs=12, sm=12, md = 12, lg = 7, xl = 7),
            dbc.Col(dcc.Graph(id='dia-Pes-pie', style={'display': 'none'}),
                            xs=12, sm=12, md = 12, lg = 5, xl = 5),           
        ], id= 'plot-row'),
        html.Hr(),
                                 
        dbc.Row([
                dbc.Card(id='table-dia', body=False, outline=False, style={'border': 'none'}),         
        ], id= 'financeiro-row'),        


        html.Hr(),
         # Add a reload button
        dbc.Row(
            dbc.Col(
                dbc.Button("Recarregar Vídeo", id="reload-button", color="primary", style = {'display': 'none'}),
                width=1
            )
        ),
        dbc.Row(html.Div(id='exchange-rate-output')),
        dbc.Row([
                dbc.Col(
                    dp.DashPlayer(
                                        id="player",
                                        url="https://stream.theiasistemas.com.br/hls/ds-test-2.m3u8",
                                        controls=False,
                                        playing=True,
                                        width="100%",
                                        height="520px",
                                        muted=True,
                                    ),
                            xs=12, sm=12, md = 12, lg = 6, xl = 6),
                dbc.Col(
                    dp.DashPlayer(
                                        id="player2",
                                        url="https://stream.theiasistemas.com.br/hls/ds-test.m3u8",
                                        playing=True,
                                        controls=False,
                                        width="100%",
                                        height="520px",
                                        muted=True,
                                    ),
                            xs=12, sm=12, md = 12, lg = 6, xl = 6),                
            ], id='video'), 
    ], body=True, outline=False, id='capture-card-dia') # fim da aba 'dia'


# Callback tab 'financeiro'
def register_callbacks(dash_app):
    @dash_app.callback(    
        Output('dia-badge-total', 'children'),
        Output('dia-badge-patas', 'children'),
        Output('dia-badge-perdidas', 'children'),
        Output('dia-badge-A', 'children'),
        Output('dia-badge-B', 'children'),
        Output('dia-badge-C', 'children'),
        Output("dia-Frango Total", "figure"),
        Output("dia-Pes-pie", "figure"),
        Output('dia-Frango Total', 'style'),
        Output('dia-Pes-pie', 'style'),
        #Output('date-picker-dia', 'disabled_days'),
        Output('date-picker-dia', 'max_date_allowed'),
        Output('table-dia','children'),
        
        Input("atualizar", 'n_clicks'),
        Input("dia-atualiza dados", "n_intervals"),
        Input("date-picker-dia","date"),
        Input("peso-F", 'value'),
        Input("valor-F", 'value'),
        Input("peso-P", 'value'),
        Input("dolar-A", 'value'),
        Input("dolar-B", 'value'),
        Input("dolar-C", 'value'),
        Input("conv", 'value'),
    )
    def dados_dia_inicial(n_clicks, n_intervals, date_value, PF, VF, PP, VA, VB, VC, USS):
        skip = 100


        #delete_older_videos()

        dis_day_paws, st_day_paws, end_day_paws = tab_functions.get_date_picker_days('paws', 'chicken', 'data')
        
        df_p, df_a = tab_functions.get_data_with_date(date_value, skip)
        df_p = df_p.sort_values(by=['hora'])
        df_a = df_a.sort_values(by=['hora'])

        if df_a.empty:
            df_a.loc[0] = [datetime.today(), 0] 
            Total_in_before = 0
        else:     
            Total_in_before = tab_functions.compute_chicken_before(df_a)
            
            
            

        if df_p.empty:
            df_p.loc[0] = [datetime.today(), 0, 0 ,0 ,0] 
        


        aX, aY = compute_display_data(df_a)
        pX, pY = compute_display_data(df_p)

        trace_total_frangos = define_line_trace(aX, aY, 'Entrada')        
        trace_total_paws = define_line_trace(pX, pY, 'Saída', 'firebrick')
        
        Total_in, Total_out, A, B, C = tab_functions.get_data_display(df_p.iloc[-1], df_a.iloc[-1])
        trace_ABC_pizza = define_pie_trace([A, B, C], tab_functions.labels)
            
            

        
        Frangos_perdidos = Total_in_before - Total_out if (Total_in_before - Total_out) > 0 else 0
        figure_Pes_pie = {'data': [trace_ABC_pizza], 'layout': define_pie_layout()}

        
        if len(aX) < 10000/skip:
            dtick = 15
        elif len(aX) < 20000/skip:
            dtick = 30
        else:
            dtick = 60
        
         # figura total    
        layout_total_frangos = define_total_frangos_layout(dtick)
        figure_total = {'data': [trace_total_frangos, trace_total_paws], 'layout': layout_total_frangos}



        print(f" PF: {PF}, A: {A}")
        PF = float(str(PF).replace(',', '.'))
        VF = float(str(VF).replace(',', '.'))
        PP = float(str(PP).replace(',', '.'))
        VA = float(str(VA).replace(',', '.'))
        VB = float(str(VB).replace(',', '.'))
        VC = float(str(VC).replace(',', '.'))
        USS = float(str(USS).replace(',', '.'))


        FRS = f'R$ {-VF*PF*(Total_in_before - Total_out):,.2f}'
        FRS = FRS.replace(',', 'X').replace('.', ',').replace('X', '.')
        QPRS= f'R$ {USS*VC*PP*(Total_out*2-(A+B+C)):,.2f}'
        QPRS= QPRS.replace(',', 'X').replace('.', ',').replace('X', '.')
        CPRS= f'R$ {USS*VC*PP*C:,.2f}'
        CPRS= CPRS.replace(',', 'X').replace('.', ',').replace('X', '.')
        TOTP= f'R$ {(-VF*PF*(Total_in_before - Total_out) + USS*VC*PP*(Total_out*2-(A+B+C)) + USS*VC*PP*C):,.2f}'
        TOTP= TOTP.replace(',', 'X').replace('.', ',').replace('X', '.')
        GARS= f'R$ {PP*VA*A*USS:,.2f}'
        GARS= GARS.replace(',', 'X').replace('.', ',').replace('X', '.')
        GBRS= f'R$ {PP*VB*B*USS:,.2f}'
        GBRS= GBRS.replace(',', 'X').replace('.', ',').replace('X', '.')
        TOTG= f'R$ {(PP*VA*A+PP*VB*B)*USS:,.2f}'
        TOTG= TOTG.replace(',', 'X').replace('.', ',').replace('X', '.')


        print(f'PP: {PP}, VB: {VB}, B: {B}, USS: {USS}')
            # f'US${GB:,.2f}'
        quantidade_data = {
                    "Part": ["Frangos Perdidos", "Queda de Patas", "Descartes de Patas C", "Total"],
                    "Valor Perdido": [FRS, QPRS, CPRS,TOTP],
                    "Ganho": ["Produção de Patas A", "Produção de Patas B", "", "Total"],
                    "Valor Ganho": [GARS, GBRS, "", TOTG]
                }
            
        df_reshaped = pd.DataFrame(quantidade_data)
        
        print(f'\n\nTabela formatada:\n{df_reshaped}')
        table_dia = dash_table.DataTable(
                data=df_reshaped.to_dict('records'),                    
                columns=[
                    {"name": "Perdas", "id": "Part"}, # type: ignore
                    {"name": "", "id": "Valor Perdido"},
                    {"name": "Ganhos", "id": "Ganho"},
                    {"name": "", "id": "Valor Ganho"}
                ],
                page_size=len(df_reshaped.index),  # Adjust the page size as needed
                style_table={'overflowX': 'auto',
                            'margin': '10px',
                            'margin-top': '10px',
                            'margin-bottom': '10px',
                            'padding':'20px'},
                style_cell={'textAlign': 'left', 'padding': '5px'},
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': len(df_reshaped)-1},  # Apply to the last row
                        'fontWeight': 'bold'  # Set the font weight to bold
                    }
                ],
            )    


        return  [Total_in, 
                Total_out, 
                Frangos_perdidos, 
                A, B, C, 
                figure_total, figure_Pes_pie,
                {'margin-right': '5px', 'border': '0px black solid'},
                {'margin-right': '5px', 'border': '0px black solid'},
                #dis_day_paws, 
                end_day_paws, table_dia
                ]
    # Callback tab 'dados dia' [fim]



    @dash_app.callback(
        [Output('player', 'key'),
        Output('player2', 'key')],
        [Input('reload-button', 'n_clicks')],
        prevent_initial_call=True
    )
    def reload_players(n_clicks):
        # Increment the key to force the players to reload
        return n_clicks, n_clicks


    @dash_app.callback(
        Output('date-picker-dia', 'date'),
        Input('date-picker-dia', 'id')  # Triggered when the page loads
    )
    def update_initial_date(_):
        global TD, YY, MM, DD, CT 
        TD, YY, MM, DD, CT = tab_functions.update_today()
        return TD  # Set to today's date or any logic to determine the initial date

'''    @dash_app.callback(
        Output('exchange-rate-output', 'children'),
        Input('date-picker-dia', 'date')
    )
    def get_exchange_rate(selected_date):
        if not selected_date:
            return "Please select a date."

        # Example URL (use your actual API endpoint and key)
        url = f"https://api.exchangeratesapi.io/{selected_date}?base=BRL&symbols=USD"

        try:
            response = requests.get(url)
            data = response.json()
            exchange_rate = data['rates']['USD']
            return f"Exchange rate on {selected_date}: 1 BRL = {exchange_rate} USD"
        except Exception as e:
            return f"Error fetching exchange rate: {str(e)}"'''


if __name__ == '__main__':   
    print('\n\nrunning locally\n\n')
    app = Flask(__name__)
    dash_app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY, '/assests/styles.css'], 
                    url_base_pathname='/', 
                    server=app)
    dash_app.title = 'THEIA - dados diarios'
    dash_app.layout = layout
    register_callbacks(dash_app)  # Register the callback with the local app
    dash_app.run_server(debug=True)