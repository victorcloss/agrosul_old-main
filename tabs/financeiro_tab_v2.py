import dash
from dash import dcc, html, Dash, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from flask import Flask
import pandas as pd
import psycopg2
import pytz
from datetime import datetime, date
import plotly.graph_objs as go


if __name__ == '__main__': 
    import tab_functions
else:    
    from tabs import tab_functions 

def read_data_of_integrado(nome):
    conn = psycopg2.connect(database="mytestdb",
                            user="postgres",
                            host='localhost',
                            password="theia@24",
                            port=5432)
    
    
    query = """
    SELECT date, chicken, paw_a, paw_b, paw_c
    FROM integrados
    WHERE name = %s
    """
    df_integrado = pd.read_sql_query(query, conn, params=(nome,))            
    conn.close()

    df_integrado.rename(columns={
        'date': 'Data',
        'chicken': 'Frangos',
        'paw_a': 'Patas A',
        'paw_b': 'Patas B',
        'paw_c': 'Patas C'
    }, inplace=True)

    return df_integrado

def define_line_trace(x, y, name = 'dados', color='royalblue', width=2):
    return go.Scatter(x=x, y=y, mode='lines', line=dict(color=color, width=width), name = name)

def define_line_layout():
    return go.Layout(title='Frangos',
                     xaxis={'title': 'Evolução', 'tickangle': 0},
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
    return go.Layout(
                     legend={'traceorder': 'normal'},
                     hoverlabel=dict(
                         font_size=20,
                         font_family=tab_functions.font_family)
                     )

def read_database_financeiro():
    conn = psycopg2.connect(database="mytestdb",
                            user="postgres",
                            host='localhost',
                            password="theia@24",
                            port=5432)
    
    
    query = f"SELECT DISTINCT name FROM integrados"
    int_names = pd.read_sql_query(query, conn)
    conn.close()
    return int_names


def compute_line_fig(df):
    fig = go.Figure()
    # Check if df is empty
    if df.empty:
        return fig 

    HH= pd.to_datetime(df['Data'], format='%Y:%m:%d').dt.strftime('%Y/%m/%d')
    # Add 'Perdas Dia' line (red)
    fig.add_trace(go.Scatter(
        x=HH, 
        y=df['Pfloat'], 
        mode='lines+markers',
        name='Perdas',  # Legend name
        line=dict(color='firebrick'),  # Set line color to blue
        marker=dict(
            color='firebrick',  # Set marker color
            size=10,  # Set marker size
            symbol='circle',  # Marker symbol (can be 'circle', 'square', 'diamond', etc.)
            #line=dict(width=2, color='DarkSlateGrey')  # Border of the marker
        ),
        hovertemplate='%{y:$.2f}'
    ))

    # Add 'Ganhos Dia' line (blue)
    fig.add_trace(go.Scatter(
        x=HH, 
        y=df['Gfloat'], 
        mode='lines+markers',
        name='Ganhos',  # Legend name
        line=dict(color='royalblue'),  # Set line color to blue
        marker=dict(
            color='royalblue',  # Set marker color
            size=10,  # Set marker size
            symbol='circle',  # Marker symbol (can be 'circle', 'square', 'diamond', etc.)
            #line=dict(width=2, color='DarkSlateGrey')  # Border of the marker
        ),
        hovertemplate='%{y:$.2f}'
    ))

        # Add 'Notas' line (green) with secondary y-axis
    fig.add_trace(go.Scatter(
        x=HH, 
        y=df['Nota'], 
        mode='lines+markers',
        name='Notas',  # Legend name
        line=dict(color='green'),  # Set line color to green
        marker=dict(
            color='green',  # Set marker color
            size=10,  # Set marker size
            symbol='square',  # Marker symbol
        ),
        hovertemplate='%{y}',  # Assuming 'Notas' is not in dollar format
        yaxis='y2'  # Assign to the secondary y-axis
    ))

    # Update layout for better readability
    fig.update_layout(
        #title='Perdas vs Ganhos Dia',
        xaxis_title='Data',
        yaxis_title='Valor (US$)',
        yaxis2=dict(
            title='Nota',  # Title for secondary y-axis
            overlaying='y',  # Overlay on the same x-axis
            side='right'  # Position the secondary y-axis on the right side
        ),
        plot_bgcolor='white',
        xaxis=dict(
            showgrid=True,  # Show grid lines for better readability
            gridcolor='lightgrey',
            tickformat='%Y-%m-%d'  # Format the x-axis as dates
        ),
        yaxis=dict(
            showgrid=True,  # Show grid lines for better readability
            gridcolor='lightgrey'
        ),
        hoverlabel=dict(
            font_size=20,  # Set font size
            font_family=tab_functions.font_family  # Set font family (e.g., Arial, Times New Roman)
        ),
        font=dict(
            size=16,  # Set font size
            family=tab_functions.font_family  # Set font family (e.g., Arial, Times New Roman)
        ) 
    )
    return fig

integrados = read_database_financeiro()
if not integrados.empty:
    integrados = integrados.sort_values(['name'])
    dropdown_options = [{'label': name, 'value': name} for name in integrados['name']]
else:
    dropdown_options = []

print(f"\n\n dropdown_options\n")

# Financeiro Tab Layout
layout = dbc.Card([            
               
                dbc.Row([                                   
                    dbc.Col([
                            dbc.Row(html.H4("Integrado:")),
                            dbc.Row(dcc.Dropdown(id='integrado-seletor', 
                                                 placeholder="Selecione um integrado",
                                                 options=dropdown_options,))
                        ],xs=12, sm=12, md=4, lg=4, xl=4),                    

                    ]),   
                
                html.Hr(),    

                dbc.Card([
                    dbc.Row([
                        
                        dbc.Col(html.H3(id='title_dia', 
                                        style={
                                            'margin-left': '30px',   # Left margin
                                            'margin-right': '20px',  # Right margin
                                            'margin-top': '20px',    # Top margin
                                            'margin-bottom': '10px'  # Bottom margin
                                        })
                        ),
                        dbc.Col(html.Img(src=r'/assets/logo2.png', 
                                         className='responsive-img',
                                         style={
                                            'margin-left': '30px',   # Left margin
                                            'margin-right': '20px',  # Right margin
                                            'margin-top': '20px',    # Top margin
                                            'margin-bottom': '10px'  # Bottom margin
                                            }),
                                xs=6, sm=4, md=4, lg=4, xl=4
                        ),
                    ]),    
                    html.H5('Dados da última entrega:', 
                            style={
                                'margin-left': '30px',   # Left margin
                                'margin-right': '20px',  # Right margin
                                'margin-top': '20px',    # Top margin
                                'margin-bottom': '10px'  # Bottom margin
                        }),                    
                    dbc.Row([                        
                        dbc.Col(dbc.Card(id='table-financeiro-dia', body=False, outline=False, style={'border': 'none'}),
                            xs=12, sm=12, md = 12, lg = 5, xl = 5),
                        dbc.Col(dcc.Graph(id='financeiro-pie', style={'margin-top': '-50px', 'border': '0px black solid'}),
                            xs=12, sm=12, md = 12, lg = 5, xl = 5)
                            ]),
                    html.Hr(),
                    html.H3("Dados totais:", 
                            style={
                                'margin-left': '30px',   # Left margin
                                'margin-right': '20px',  # Right margin
                                'margin-top': '20px',    # Top margin
                                'margin-bottom': '10px'  # Bottom margin
                        }),
                    dcc.Graph(id='graph-geral',
                              style={
                                'margin-left': '30px',   # Left margin
                                'margin-right': '20px',  # Right margin
                                'margin-top': '20px',    # Top margin
                                'margin-bottom': '10px'  # Bottom margin
                        }),
                    dbc.Card(id='table-financeiro-geral', body=True, outline=False, style={'border': 'none'}), 
                    # Button to trigger PDF export
                    
                    ], style={'display': 'none',}, id = 'print'),
                    dbc.Button("Export to PDF", className="mr-1", id='export-button-financeiro', n_clicks=0, style={'display': 'none'}),                    
                    dcc.Download(id="pdf-download")
], body=True, outline=False, id="capture-card-financeiro")# fim aba financeiro

# Callback tab 'financeiro'
def register_callbacks_financeiro(dash_app):
    @dash_app.callback(         
        Output('print', 'style'),
        Output('title_dia', 'children'),   
        Output("financeiro-pie", "figure"),  
        Output('table-financeiro-dia','children'),
        Output('table-financeiro-geral','children'),
        Output('graph-geral','figure'),
        Output('export-button-financeiro','style'),
        Input("integrado-seletor", 'value'),
        Input("dolar-A", 'value'),
        Input("dolar-B", 'value'),
        Input("dolar-C", 'value'),
        Input("peso-P", 'value')
    )
    def calback_financeiro(nome, dA, dB, dC, peso):
        dA = str(dA).replace(',', '.')
        dB = str(dB).replace(',', '.')
        dC = str(dC).replace(',', '.')
        peso = str(peso).replace(',', '.')
        
        dA = float(dA)
        dB = float(dB)
        dC = float(dC)
        peso = float(peso)
        # here we get all the data from the integrado
        print(f'\n\n seleção vinda do callback: {nome} ')
        if nome is not None:
            resultado_style={'display': 'block'}
            download_style={'display': 'block', 'margin': '20px'}
            df = read_data_of_integrado(nome)
            df = df.sort_values('Data')

            print(f'\n\n{df}')
            A = df['Patas A'].iloc[-1]
            B = df['Patas B'].iloc[-1]
            C = df['Patas C'].iloc[-1]
            data = df['Data'].iloc[-1].strftime('%d/%m/%Y')
            # print(f'\n\n {title} \n\n {type(title)}')
            nota = round(3 * A / (A+B+C) + 7 * ( 1 - C/ (A+B+C)), 2)



            title_dia = f'{nome} - ({nota})'

            df['Gfloat'] = (df["Patas A"]*dA + df["Patas B"]*dB + df["Patas C"]*dC)*peso            
            df['Pfloat'] = (df["Patas B"]*(dA-dB) + df["Patas C"]*(dA-dC))*peso
            
            # Create the new row where the first column is "Total"
            total_row = df.iloc[:, 1:].sum()

            # Convert the sum to a row and append the "Total" label to the first column
            total_row = pd.DataFrame([['Total'] + total_row.tolist()], columns=df.columns)

            # Append the row to the original DataFrame
            df = pd.concat([df, total_row], ignore_index=True)
            df['Ganhos'] = df['Gfloat'].apply(lambda x: f"US$ {x:,.2f}")
            df['Perdas'] = df['Pfloat'].apply(lambda x: f"US$ -{x:,.2f}")

            
            df['Perdas'] = df['Perdas'].str.replace(',', 'X')
            df['Perdas'] = df['Perdas'].str.replace('.', ',')
            df['Perdas'] = df['Perdas'].str.replace('X', '.')
            




            TQ = df["Patas A"][0]+df["Patas B"][0]+df["Patas C"][0] 

            GA = df["Patas A"][0]*float(dA)*float(peso)
            GAs= f'US$ {GA:,.2f}'
            GAs= GAs.replace(',', 'X').replace('.', ',').replace('X', '.')
            GB = df["Patas B"][0]*float(dB)*float(peso)
            GBs= f'US$ {GB:,.2f}'
            GBs= GBs.replace(',', 'X').replace('.', ',').replace('X', '.')
            GC= df["Patas C"][0]*float(dC)*float(peso)
            GCs= f'US$ {GC:,.2f}'
            GCs= GCs.replace(',', 'X').replace('.', ',').replace('X', '.')
            GT = GA+GB+GC
            GTs= f'US$ {GT:,.2f}'
            GTs= GTs.replace(',', 'X').replace('.', ',').replace('X', '.')
            

            PB = df["Patas B"][0]*(float(dB)-float(dA))*float(peso)
            PBs= f'US$ {PB:,.2f}'
            PBs= PBs.replace(',', 'X').replace('.', ',').replace('X', '.')
            PC = df["Patas C"][0]*(float(dC)-float(dA))*float(peso)
            PCs= f'US$ {PC:,.2f}'
            PCs= PCs.replace(',', 'X').replace('.', ',').replace('X', '.')

            PT = PB+PC
            PTs= f'US$ {PT:,.2f}'
            PTs= PTs.replace(',', 'X').replace('.', ',').replace('X', '.')




            quantidade_data = {
                    "Part": ["Patas A", "Patas B", "Patas C", "Totais"],
                    "Quantidade": [df["Patas A"][0], df["Patas B"][0], df["Patas C"][0], TQ],
                    "Ganho": [GAs, GBs, GCs, GTs],
                    "Perda": ["0", PBs, PCs, PTs]
                }
            
            df_reshaped = pd.DataFrame(quantidade_data)
            print(f'\n\nTabela formatada:\n{df_reshaped}')
            table_dia = dash_table.DataTable(
                    data=df_reshaped.to_dict('records'),                    
                    columns=[
                        {"name": data, "id": "Part"},
                        {"name": "Quantidade", "id": "Quantidade"},
                        {"name": "Ganho", "id": "Ganho"},
                        {"name": "Perda", "id": "Perda"}
                    ],
                    page_size=len(df_reshaped.index),  # Adjust the page size as needed
                    style_table={'overflowX': 'auto',
                                'margin-left': '40px',
                                'margin-right': '20px',
                                'margin-top': '80px',
                                'margin-bottom': '10px'},
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

            
            df_table = df.drop(['Gfloat', 'Pfloat' ], axis=1)
            df_table['Nota'] = round(3 * df['Patas A'] / (df['Patas A']+df['Patas B']+df['Patas C']) + 7 * (
                1 - df['Patas C'] / (df['Patas A']+df['Patas B']+df['Patas C'])), 2)
            df['Nota'] = df_table['Nota'] 
            print(f'\n\nDf com ganhos e perdas:\n {df_table}')
            table_geral = dash_table.DataTable(
                    data=df_table.to_dict('records'),                    
                    columns=[{"name": col, "id": col} for col in df_table.columns],
                    page_size=len(df_table.index)+5,  # Adjust the page size as needed
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', 'padding': '5px'},
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': len(df_table)-1},  # Apply to the last row
                            'fontWeight': 'bold'  # Set the font weight to bold
                        }
                    ],
                )
            


        else:
            A = 0,
            B = 0,
            C = 0,
            data = ' '        
            table_geral = []
            title_dia= None
            table_dia = []
            resultado_style = {'display': 'none'}
            download_style = {'display': 'none'}
            df = pd.DataFrame([])
            
            
            
            
            
        
        trace_ABC_pie = define_pie_trace([A, B, C], tab_functions.labels)
        figure_pie = {'data': [trace_ABC_pie], 'layout': define_pie_layout()}
        figure_geral = compute_line_fig(df.iloc[:-1]) #{'data': [trace_total_ganhos, trace_total_perdas], 'layout': define_line_layout}
        
        return resultado_style, title_dia, figure_pie, table_dia, table_geral, figure_geral, download_style
    '''{
                                'margin-left': '30px',   # Left margin
                                'margin-right': '20px',  # Right margin
                                'margin-top': '20px',    # Top margin
                                'margin-bottom': '10px'  # Bottom margin
                        }'''

    # the function below needs css_file and java_script file as obtained from
    # https://community.plotly.com/t/exporting-multi-page-dash-app-to-pdf-with-entire-layout/37953/33
    # user Sarvesh04
    dash_app.clientside_callback(
        """
        function(n_clicks){
            if(n_clicks > 0){
                var opt = {
                    margin: [-10, 1, -10, -2],
                    filename: 'file.pdf',
                    image: { type: 'jpeg', quality: 0.98 },
                    html2canvas: { width: 1400, heigth: 25, scale: 2},
                    jsPDF: { unit: 'cm', format: 'a3', orientation: 'p' },
                    
                };
                html2pdf().from(document.getElementById("print")).set(opt).save();
            }
        }
        """,
        Output('js', 'n_clicks'),
        Input('js', 'n_clicks')
    )
            


if __name__ == '__main__':   
    print('\n\nrunning locally\n\n')
    app = Flask(__name__)
    dash_app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY, '/assests/styles.css'], 
                    url_base_pathname='/', 
                    server=app)
    dash_app.title = 'THEIA - financeiro'
    dash_app.layout = layout
    register_callbacks_financeiro(dash_app)  # Register the callback with the local app
    dash_app.run_server(debug=True)