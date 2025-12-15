import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- Configuração da Página ---
st.set_page_config(page_title="Dashboard Financeiro", layout="wide", menu_items=None)

# --- Ocultar itens padrão do Streamlit (Menu, Footer, Header) ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- Funções de Carregamento e Tratamento ---
@st.cache_data
def carregar_dados():
    # Carrega os arquivos
    try:
        df_receber = pd.read_csv("Contas a receber.csv")
        df_pagar = pd.read_csv("Contas a pagar.csv")
    except FileNotFoundError:
        st.error("Arquivos CSV não encontrados. Verifique se 'Contas a receber.csv' e 'Contas a pagar.csv' estão no repositório.")
        return None, None

    # Função auxiliar para tratar datas
    def tratar_datas(df, colunas):
        for col in colunas:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
        return df

    # Tratamento Receber
    df_receber = tratar_datas(df_receber, ['Data Realizado', 'Vencimento', 'Competência'])
    df_receber['Valor Realizado'] = pd.to_numeric(df_receber['Valor Realizado'], errors='coerce').fillna(0)
    df_receber['Valor (R$)'] = pd.to_numeric(df_receber['Valor (R$)'], errors='coerce').fillna(0)
    
    # Tratamento Pagar
    df_pagar = tratar_datas(df_pagar, ['Data Realizado', 'Vencimento', 'Competência'])
    df_pagar['Valor Realizado'] = pd.to_numeric(df_pagar['Valor Realizado'], errors='coerce').fillna(0)

    return df_receber, df_pagar

df_receber, df_pagar = carregar_dados()

if df_receber is not None and df_pagar is not None:

    # --- Sidebar: Filtros ---
    st.sidebar.header("Filtros")
    anos_disponiveis = sorted(df_receber['Data Realizado'].dt.year.dropna().unique().astype(int))
    ano_selecionado = st.sidebar.selectbox("Selecione o Ano", anos_disponiveis, index=len(anos_disponiveis)-1)
    
    # Filtrando dados pelo ano (para gráficos de fluxo)
    df_rec_ano = df_receber[df_receber['Data Realizado'].dt.year == ano_selecionado].copy()
    df_pag_ano = df_pagar[df_pagar['Data Realizado'].dt.year == ano_selecionado].copy()

    st.title(f"📊 Dashboard Financeiro - {ano_selecionado}")

    # --- 1. KPIs Principais (Cards) ---
    faturamento_total = df_rec_ano['Valor Realizado'].sum()
    gastos_totais = df_pag_ano['Valor Realizado'].sum()
    resultado = faturamento_total - gastos_totais
    
    # Cálculo Inadimplência (Total acumulado vencido e não pago até hoje)
    hoje = pd.to_datetime(datetime.now().date())
    inadimplencia_total = df_receber[
        (df_receber['Quitado'] == 'Não') & 
        (df_receber['Vencimento'] < hoje)
    ]['Valor (R$)'].sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Faturamento (Ano)", f"R$ {faturamento_total:,.2f}")
    col2.metric("Gastos Totais (Ano)", f"R$ {gastos_totais:,.2f}")
    col3.metric("Resultado (Ano)", f"R$ {resultado:,.2f}", delta_color="normal")
    col4.metric("Inadimplência (Total)", f"R$ {inadimplencia_total:,.2f}", delta_color="inverse")

    st.divider()

    # --- 2. Evolução do Faturamento e Inadimplência ---
    col_evo1, col_evo2 = st.columns(2)
    
    with col_evo1:
        st.subheader("Evolução do Faturamento")
        # Agrupa por mês
        df_fat_mes = df_rec_ano.groupby(df_rec_ano['Data Realizado'].dt.to_period('M'))['Valor Realizado'].sum().reset_index()
        df_fat_mes['Data Realizado'] = df_fat_mes['Data Realizado'].dt.to_timestamp()
        
        fig_fat = px.bar(df_fat_mes, x='Data Realizado', y='Valor Realizado', text_auto='.2s')
        st.plotly_chart(fig_fat, use_container_width=True)

    with col_evo2:
        st.subheader("Evolução da Inadimplência (Vencimento)")
        # Inadimplência baseada na data de vencimento (histórico)
        df_inad = df_receber[(df_receber['Quitado'] == 'Não') & (df_receber['Vencimento'] < hoje)]
        # Filtra apenas o ano selecionado para visualizar a origem da dívida
        df_inad_ano = df_inad[df_inad['Vencimento'].dt.year == ano_selecionado]
        
        if not df_inad_ano.empty:
            df_inad_mes = df_inad_ano.groupby(df_inad_ano['Vencimento'].dt.to_period('M'))['Valor (R$)'].sum().reset_index()
            df_inad_mes['Vencimento'] = df_inad_mes['Vencimento'].dt.to_timestamp()
            fig_inad = px.line(df_inad_mes, x='Vencimento', y='Valor (R$)', markers=True, color_discrete_sequence=['red'])
            st.plotly_chart(fig_inad, use_container_width=True)
        else:
            st.info("Sem inadimplência registrada para o período selecionado.")

    # --- 3. Evolução do Caixa (Acumulado) ---
    st.subheader("Evolução do Caixa (Fluxo Acumulado)")
    
    # Prepara fluxo diário
    fluxo_receita = df_rec_ano[['Data Realizado', 'Valor Realizado']].rename(columns={'Valor Realizado': 'Valor'})
    fluxo_receita['Tipo'] = 'Entrada'
    
    fluxo_despesa = df_pag_ano[['Data Realizado', 'Valor Realizado']].rename(columns={'Valor Realizado': 'Valor'})
    fluxo_despesa['Valor'] = fluxo_despesa['Valor'] * -1 # Negativo para saída
    fluxo_despesa['Tipo'] = 'Saída'
    
    df_fluxo = pd.concat([fluxo_receita, fluxo_despesa]).sort_values('Data Realizado')
    df_fluxo['Saldo Acumulado'] = df_fluxo['Valor'].cumsum()
    
    fig_caixa = px.area(df_fluxo, x='Data Realizado', y='Saldo Acumulado', title="Saldo Acumulado ao longo do tempo")
    st.plotly_chart(fig_caixa, use_container_width=True)

    st.divider()

    # --- 4. Análises de Gastos e Categorias ---
    col_cat1, col_cat2 = st.columns(2)

    with col_cat1:
        st.subheader("Faturamento Segregado (Top 10 Categorias)")
        df_cat_rec = df_rec_ano.groupby('Categoria')['Valor Realizado'].sum().sort_values(ascending=True).tail(10)
        fig_cat_rec = px.bar(df_cat_rec, orientation='h', text_auto='.2s')
        st.plotly_chart(fig_cat_rec, use_container_width=True)

    with col_cat2:
        st.subheader("Principais Gastos (Pizza)")
        df_cat_pag = df_pag_ano.groupby('Categoria')['Valor Realizado'].sum().reset_index()
        # Agrupar pequenos gastos em "Outros" para limpar o gráfico
        limit = df_cat_pag['Valor Realizado'].sum() * 0.02 # Menor que 2% vira Outros
        df_cat_pag.loc[df_cat_pag['Valor Realizado'] < limit, 'Categoria'] = 'Outros'
        fig_pie = px.pie(df_cat_pag, values='Valor Realizado', names='Categoria')
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- 5. Análise Vertical (Faturamento x Gastos Específicos) ---
    st.subheader("Análise Vertical: Impacto no Faturamento")
    
    # Definição simples de grupos baseada em strings (ajuste as palavras chaves conforme seus dados reais)
    impostos = df_pag_ano[df_pag_ano['Categoria'].str.contains('Imposto|DAS|DARF|ISS|PIS|COFINS', case=False, na=False)]['Valor Realizado'].sum()
    folha = df_pag_ano[df_pag_ano['Categoria'].str.contains('Folha|Salário|Pró-labore|Pessoal|INSS|FGTS', case=False, na=False)]['Valor Realizado'].sum()
    
    # Tentativa de identificar terceirização/quarteirização
    terceiros = df_pag_ano[df_pag_ano['Categoria'].str.contains('Terceir|Serviço|PJ|Consultoria', case=False, na=False)]['Valor Realizado'].sum()
    
    # Monta tabela de análise
    dados_analise = {
        'Grupo': ['Impostos', 'Folha / Pessoal', 'Terceirização/Serviços', 'Margem Bruta (Aprox)'],
        'Valor (R$)': [impostos, folha, terceiros, faturamento_total - (impostos + folha + terceiros)],
    }
    df_analise = pd.DataFrame(dados_analise)
    df_analise['% do Faturamento'] = (df_analise['Valor (R$)'] / faturamento_total) * 100
    
    st.dataframe(df_analise.style.format({'Valor (R$)': 'R$ {:,.2f}', '% do Faturamento': '{:.1f}%'}), use_container_width=True)
    
    # Gráfico de barras empilhadas para visualização
    fig_av = px.bar(df_analise, x='Grupo', y='% do Faturamento', text_auto='.1f', title="Peso de cada grupo sobre o Faturamento Total")
    st.plotly_chart(fig_av, use_container_width=True)