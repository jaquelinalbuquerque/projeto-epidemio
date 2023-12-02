#Instalações
''' no vscode
    1. py -m pip install virtualenv
    2. py -m venv venv
    3. .\venv\Scripts\activate
    4. deactivate para desativar
    5. py -m pip install dash
    6. pip instsall openpyxl
    7. py -m pip install dash-bootstrap-components
'''
# Bibliotecas importadas
import dash
from dash import Dash, html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from flask import Flask, config, render_template, request
import datetime
import plotly.io as pio

# Inicializa o Flask
server = Flask(__name__)

# Inicializa o aplicativo Dash
#app = dash.Dash(__name__, server=server)
app = Dash(external_stylesheets=[dbc.themes.SLATE])


# Acessa a base de dados
df_sv2 = pd.read_excel ('basesv2.xlsx')
df_unidades = pd.read_excel ('unidades.xlsx')


#ETL DA BASE DE DADOS -------------------------------------------

# 1. Deletar linhas de semana negativa
df_sv2 = df_sv2[df_sv2["DATA_NOTIFICACAO"] != "SEMANA NEGATIVA"]

# 2. Inserir STS no df_sv2 com base no df_unidades (procv em unidades)
df_sv2 = pd.merge(df_sv2, df_unidades[['CNES', 'STS']], on='CNES', how='left')

# 3. Para as unidades notificantes diferentes da lista de unidade, mudar nome para "OUTRA"
df_sv2.loc[~df_sv2['UNIDADE_NOTIFICANTE'].isin(df_unidades['UNIDADE']), 'UNIDADE_NOTIFICANTE'] = 'OUTRA'

# 4. Criar coluna "FONTE_ABRANGENCIA" com valores interna (abrangência igual a informante) ou externa (abrangência diferente da informante)

# Função para determinar "Interna" ou "Externa"
def define_fonte_abrangencia(linha):
    if linha['UNIDADE_NOTIFICANTE'] == linha['UNIDADE_ABRANGENCIA']:
        return 'Interna'
    else:
        return 'Externa'

# Aplica a função à coluna "FONTE_ABRANGENCIA" usando apply
df_sv2['FONTE_ABRANGENCIA'] = df_sv2.apply(define_fonte_abrangencia, axis=1)   #axis1, significa eixo 1 ou linha a linha

# 5. Corrigir formato de datas

#Função Corrigir data
def corrigir_formato_data(data):
    try:
        if isinstance(data, str):
            # Tenta converter texto no formato 'dd/mm/aaaa' em objeto de data
            return datetime.datetime.strptime(data, '%d/%m/%Y').strftime('%d/%m/%Y')
        elif isinstance(data, int):
            # Tenta converter número Excel em objeto de data
            data_referencia_excel = datetime.datetime(1899, 12, 30)
            return (data_referencia_excel + datetime.timedelta(days=data)).strftime('%d/%m/%Y')
        elif isinstance(data, datetime.datetime):
            # Se já for um objeto de data, mantém da mesma forma
            return data.strftime('%d/%m/%Y')
        else:
            return 'Formato de data não reconhecido'
    except Exception as e:
        return 'Erro na conversão: ' + str(e)
# 5.1 Aplicar função corrigir_formato_data
df_sv2['DATA_NOTIFICACAO'] = df_sv2['DATA_NOTIFICACAO'].apply(corrigir_formato_data)
df_sv2['NASCIMENTO'] = df_sv2['NASCIMENTO'].apply(corrigir_formato_data)

# 6. Alterar valor da coluna SEMANA para ano+semana
# Primeiro, manter apenas os dois dígitos numéricos da coluna SEMANA
df_sv2['SEMANA'] = df_sv2['SEMANA'].str.extract(r'(\d{2})')

# concatenar os dois dígitos da coluna SEMANA com a coluna ANO_NOTIFICACAO
df_sv2['SEMANA'] = df_sv2['ANO_NOTIFICACAO'].astype(str) + df_sv2['SEMANA'].astype(str).str.zfill(2)

# 7. Cria a coluna "QTDE-TOTAL" duplicada de "QTDE-COVID"
df_sv2['QTDE-TOTAL'] = df_sv2['QTDE-COVID']

# Preenche os valores nulos na coluna "QTDE-TOTAL" com 1
df_sv2['QTDE-TOTAL'].fillna(1, inplace=True)


df_sv2.tail()[['DOENCA_AGRAVO', 'QTDE-COVID', 'QTDE-TOTAL']]

# 8. Contar quantidade moradores de rua

def marcar_situacao_rua(valor):
  if isinstance(valor, str) and ('situacao de rua' in valor.lower() or 'situação de rua' in valor.lower() or 'situacão de rua' in valor.lower() or 'situaçao de rua' in valor.lower()):
    return 'SIM'
  else:
    return ''

#Aplicando a função à nova coluna:

df_sv2['SITUACAO_RUA'] = df_sv2['OBSERVACAO'].apply(marcar_situacao_rua)

# 1. Criar medida Total de notificações
total_notificacoes = df_sv2['QTDE-TOTAL'].sum()
# ou total_notificacoes = sum(df_sv2['QTDE-TOTAL'])
total_notificacoes

# 2. Top 10 agravos
# Agrupa por tipo de agravo e soma a quantidade total de notificacoes
ranking_agravos = df_sv2.groupby('DOENCA_AGRAVO')['QTDE-TOTAL'].sum().reset_index()

#Ordena por quantidade em ordem decrescente
ranking_agravos = ranking_agravos.sort_values(by='QTDE-TOTAL', ascending=False)

#Cria um ranking
ranking_agravos['Rank'] = ranking_agravos['QTDE-TOTAL'].rank(ascending=False, method='min')

#Exibe o ranking 
#print(ranking_agravos)


# FIM DO ETL DA BASE DE DADOS ------------------------------------









# cria o gráfico
pio.templates.default = "plotly_dark"


fig = px.bar(df_sv2, x="SEMANA", y="QTDE-TOTAL", color="STS", barmode="group", title='Notificações Por STS')  
fig.update_layout(template='plotly_dark')

fig_pizza = px.pie(df_sv2, values='QTDE-TOTAL', names='INFORMANTE', title='Notificações Por Unidade')
fig_pizza.update_layout(template='plotly_dark')

fig_line = px.line(df_sv2, x="SEMANA", y="QTDE-TOTAL", color='DOENCA_AGRAVO', title='Linha temporal de notificacões por agravo')
fig_line.update_layout(template='plotly_dark')

#cria opções de seleção para filtrar o gráfico
    #Filtro de STS
opcoes_sts = list(df_sv2['STS'].unique())
opcoes_sts.append("Todos os Territórios")
    #Filtro de Agravos
opcoes_agravo = list(df_sv2['DOENCA_AGRAVO'].unique())
opcoes_agravo.append("Todos os Agravos")










# Cria o layout, podendo usar itens de html ou itens de gráfico (dcc)
app.layout = html.Div(children=[
    html.H1(children='Semana Epidemiológica - SV2', style={'margin-bottom': '30px', 'margin-top': '30px', 'textAlign': 'center'}),
    html.H4(children='Relatório Mensal de Monitoramento de Agravos Por Território (STS)', style={'margin-bottom': '30px', 'margin-top': '30px', 'textAlign': 'center'}),
    html.Div(children='''
        
    Os dados abaixo são referentes aos registros dos agravos de notificação obrigatória, por semana epidemiológica.
    
    '''),
    html.Br(),
    dcc.Dropdown(opcoes_sts, value='Todos os Territórios', id='lista_STS'),
    html.Br(),
    dcc.Dropdown(opcoes_agravo, value='Todos os Agravos', id='lista_agravos'),
    html.Br(),


   
    dcc.DatePickerRange(
        id='date-picker-range',
        start_date=df_sv2['DATA_NOTIFICACAO'].min(),
        end_date=df_sv2['DATA_NOTIFICACAO'].max(),
        display_format='DD/MM/YYYY'
    ),
    html.Br(),
   




    html.H2(children='Notificações Por STS', style={'margin-bottom': '30px', 'margin-top': '30px', 'textAlign': 'center'}),

    dcc.Graph(
        id='grafico_quantidade_agravos',
        figure=fig
    ),

    html.H2(children='Notificações Por Unidade', style={'margin-bottom': '30px', 'margin-top': '30px', 'textAlign': 'center'}),

    dcc.Graph(
        id='grafico_pizza_notificacoes',
        figure=fig_pizza
    ),

    html.H2(children='Linha Temporal de Notificações Por Agravo', style={'margin-bottom': '30px', 'margin-top': '30px', 'textAlign': 'center'}),

    dcc.Graph(
        id='grafico_line_agravos',
        figure=fig_line
    ),

    
    html.Div([
        html.H2(children='Ranking de Agravos', style={'margin-bottom': '30px', 'margin-top': '30px', 'textAlign': 'center'}),
        html.Br(),
        dash_table.DataTable(
            id='tabela-ranking-agravos',
            columns=[
                {"name": col, "id": col} for col in ranking_agravos.columns
            ],
            data=ranking_agravos.head(10).to_dict('records'),
            style_table={'width': '50%', 'margin': 'auto'},
            style_header={
                'backgroundColor': '#333',  # Cor de fundo para o cabeçalho
                'color': 'white'  # Cor do texto para o cabeçalho
            },
            style_cell={
                'backgroundColor': '#444',  # Cor de fundo para as células
                'color': 'white'  # Cor do texto para as células
            },
            page_current=0,
            page_size=10,
        )
    ])

],
style={'margin': 'auto', 'width': '70%'} 
)

# Define a rota do Flask para o Dash
@server.route('/')
def index():
    return 'Hello, Gráfico'

@app.callback(
    Output('grafico_quantidade_agravos', 'figure'),
    Output('grafico_pizza_notificacoes', 'figure'),
    Output('grafico_line_agravos', 'figure'),
    [Input('lista_STS', 'value'),
    Input('lista_agravos', 'value')]
    #Input('date-picker-range', 'start_date'),
    #Input('date-picker-range', 'end_date')]
)



def update_output(sts_selecionada, agravo_selecionado):
    if (sts_selecionada == "Todos os Territórios" and agravo_selecionado == "Todos os Agravos"):
        fig = px.bar(df_sv2, x="SEMANA", y="QTDE-TOTAL", color="STS", barmode="group", title='Notificações Por STS')
        fig_pizza = px.pie(df_sv2, values='QTDE-TOTAL', names='INFORMANTE', title='Notificações Por Unidade')
        fig_line = px.line(df_sv2, x="SEMANA", y="QTDE-TOTAL", color='DOENCA_AGRAVO', title='Linha temporal de notificacões por agravo')
        

    elif (sts_selecionada == "Todos os Territórios" and agravo_selecionado != "Todos os Agravos"):
        tabela_filtrada = df_sv2.loc[(df_sv2['DOENCA_AGRAVO']==agravo_selecionado)]
        fig = px.bar(tabela_filtrada, x="SEMANA", y="QTDE-TOTAL", color="STS", barmode="group", title='Notificações Por STS')
        fig_pizza = px.pie(tabela_filtrada, values='QTDE-TOTAL', names='INFORMANTE', title='Notificações Por Unidade')
        fig_line = px.line(df_sv2, x="SEMANA", y="QTDE-TOTAL", color='DOENCA_AGRAVO', title='Linha temporal de notificacões por agravo')

    elif (sts_selecionada != "Todos os Territórios" and agravo_selecionado == "Todos os Agravos"):
        tabela_filtrada = df_sv2.loc[(df_sv2['STS']==sts_selecionada)]
        fig = px.bar(tabela_filtrada, x="SEMANA", y="QTDE-TOTAL", color="STS", barmode="group", title='Notificações Por STS')
        fig_pizza = px.pie(tabela_filtrada, values='QTDE-TOTAL', names='INFORMANTE', title='Notificações Por Unidade')
        fig_line = px.line(tabela_filtrada, x="SEMANA", y="QTDE-TOTAL", color='DOENCA_AGRAVO', title='Linha temporal de notificacões por agravo')
    else:
        tabela_filtrada = df_sv2.loc[(df_sv2['STS']==sts_selecionada) & (df_sv2['DOENCA_AGRAVO']==agravo_selecionado)]
        fig = px.bar(tabela_filtrada, x="SEMANA", y="QTDE-TOTAL", color="STS", barmode="group", title='Notificações Por STS')
        fig_pizza = px.pie(tabela_filtrada, values='QTDE-TOTAL', names='INFORMANTE', title='Notificações Por Unidade')
        fig_line = px.line(tabela_filtrada, x="SEMANA", y="QTDE-TOTAL", color='DOENCA_AGRAVO', title='Linha temporal de notificacões por agravo')
    return fig, fig_pizza, fig_line





'''
def update_output(start_date, end_date, sts_selecionada, agravo_selecionado):
    filtered_df = df_sv2[(df_sv2['DATA_NOTIFICACAO'] >= start_date) & (df_sv2['DATA_NOTIFICACAO'] <= end_date)]

    if (sts_selecionada == "Todos os Territórios" and agravo_selecionado == "Todos os Agravos"):
        fig = px.bar(filtered_df, x="SEMANA", y="QTDE-TOTAL", color="STS", barmode="group", title='Notificações Por STS')
        fig_pizza = px.pie(filtered_df, values='QTDE-TOTAL', names='INFORMANTE', title='Notificações Por Unidade')
        fig_line = px.line(filtered_df, x="SEMANA", y="QTDE-TOTAL", color='DOENCA_AGRAVO', title='Linha temporal de notificações por agravo')

    elif (sts_selecionada == "Todos os Territórios" and agravo_selecionado != "Todos os Agravos"):
        tabela_filtrada = filtered_df.loc[(filtered_df['DOENCA_AGRAVO'] == agravo_selecionado)]
        fig = px.bar(tabela_filtrada, x="SEMANA", y="QTDE-TOTAL", color="STS", barmode="group", title='Notificações Por STS')
        fig_pizza = px.pie(tabela_filtrada, values='QTDE-TOTAL', names='INFORMANTE', title='Notificações Por Unidade')
        fig_line = px.line(filtered_df, x="SEMANA", y="QTDE-TOTAL", color='DOENCA_AGRAVO', title='Linha temporal de notificações por agravo')

    elif (sts_selecionada != "Todos os Territórios" and agravo_selecionado == "Todos os Agravos"):
        tabela_filtrada = filtered_df.loc[(filtered_df['STS'] == sts_selecionada)]
        fig = px.bar(tabela_filtrada, x="SEMANA", y="QTDE-TOTAL", color="STS", barmode="group", title='Notificações Por STS')
        fig_pizza = px.pie(tabela_filtrada, values='QTDE-TOTAL', names='INFORMANTE', title='Notificações Por Unidade')
        fig_line = px.line(tabela_filtrada, x="SEMANA", y="QTDE-TOTAL", color='DOENCA_AGRAVO', title='Linha temporal de notificações por agravo')

    else:
        tabela_filtrada = filtered_df.loc[(filtered_df['STS'] == sts_selecionada) & (filtered_df['DOENCA_AGRAVO'] == agravo_selecionado)]
        fig = px.bar(tabela_filtrada, x="SEMANA", y="QTDE-TOTAL", color="STS", barmode="group", title='Notificações Por STS')
        fig_pizza = px.pie(tabela_filtrada, values='QTDE-TOTAL', names='INFORMANTE', title='Notificações Por Unidade')
        fig_line = px.line(tabela_filtrada, x="SEMANA", y="QTDE-TOTAL", color='DOENCA_AGRAVO', title='Linha temporal de notificações por agravo')


    return fig, fig_pizza, fig_line
'''


#para colocar o site no ar
if __name__ == '__main__':
    app.run_server(debug=True)