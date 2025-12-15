import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import locale

# --- Configuração da Página ---
st.set_page_config(page_title="Dashboard Financeiro", layout="wide")

# Configuração de locale para português
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
    except locale.Error:
        pass

# --- CSS Personalizado ---
hide_st_style = """
            <style>
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- Upload de Arquivos CSV ---
st.subheader("📁 Atualizar Bases de Dados")
col1, col2 = st.columns(2)
with col1:
    uploaded_receber = st.file_uploader("Upload Contas a receber.csv", type="csv", key="receber")
    uploaded_mov = st.file_uploader("Upload movimentacoes-financeiras.csv", type="csv", key="mov")
with col2:
    uploaded_pagar = st.file_uploader("Upload Contas a pagar.csv", type="csv", key="pagar")
    uploaded_inad = st.file_uploader("Upload inadimplencia.csv", type="csv", key="inad")

st.markdown("---")

# --- Funções de Carregamento e Tratamento ---
@st.cache_data
def carregar_dados(file_receber, file_pagar, file_mov, file_inad):
    df_receber, df_pagar, df_mov, df_inad = None, None, None, None

    # Função auxiliar para tratar datas (dayfirst=True para formato brasileiro)
    def tratar_datas(df, colunas):
        for col in colunas:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
        return df

    try:
        # Carregar Movimentações (Principal)
        if file_mov is not None:
            df_mov = pd.read_csv(file_mov)
        else:
            try:
                df_mov = pd.read_csv("movimentacoes-financeiras.csv")
            except FileNotFoundError:
                pass
        
        if df_mov is not None:
            # --- NOVO FILTRO: Remover Transferências ---
            # Remove linhas onde a coluna 'Transferência' é marcada como 'Sim'
            if 'Transferência' in df_mov.columns:
                df_mov = df_mov[df_mov['Transferência'] != 'Sim'] 
            
            df_mov = tratar_datas(df_mov, ['Data Realizado', 'Vencimento', 'Competência'])
            
            # Tratamento de valores numéricos
            cols_valor = ['Valor Realizado', 'Valor (R$)']
            for col in cols_valor:
                if col in df_mov.columns:
                     if df_mov[col].dtype == 'object':
                        df_mov[col] = pd.to_numeric(df_mov[col].str.replace(',', '.'), errors='coerce').fillna(0)
                     else:
                        df_mov[col] = pd.to_numeric(df_mov[col], errors='coerce').fillna(0)

        # Carregar Inadimplência
        if file_inad is not None:
            df_inad = pd.read_csv(file_inad)
        else:
            try:
                df_inad = pd.read_csv("inadimplencia.csv")
            except FileNotFoundError:
                pass
        
        if df_inad is not None:
            df_inad = tratar_datas(df_inad, ['Últ. Pagamento'])
            if 'Valor (R$)' in df_inad.columns:
                if df_inad['Valor (R$)'].dtype == 'object':
                    df_inad['Valor (R$)'] = pd.to_numeric(df_inad['Valor (R$)'].str.replace(',', '.'), errors='coerce').fillna(0)
                else:
                    df_inad['Valor (R$)'] = pd.to_numeric(df_inad['Valor (R$)'], errors='coerce').fillna(0)

        # Carregar Contas a Receber (Opcional)
        if file_receber is not None:
            df_receber = pd.read_csv(file_receber)
        # Carregar Contas a Pagar (Opcional)
        if file_pagar is not None:
            df_pagar = pd.read_csv(file_pagar)

    except Exception as e:
        st.error(f"Erro ao carregar arquivos: {e}")
        return None, None, None, None

    return df_receber, df_pagar, df_mov, df_inad

# Carrega os dados
df_receber, df_pagar, df_mov, df_inad = carregar_dados(uploaded_receber, uploaded_pagar, uploaded_mov, uploaded_inad)

if df_mov is not None:
    
    # --- Layout do Topo (Título + Filtro) ---
    col_titulo, col_filtro = st.columns([3, 1])

    # Filtra apenas anos válidos
    anos_disponiveis = sorted(df_mov['Data Realizado'].dt.year.dropna().unique().astype(int))
    
    if not anos_disponiveis:
        st.warning("Não há dados de datas válidas no arquivo de movimentações (após filtros).")
        st.stop()

    idx_ano = len(anos_disponiveis)-1 if anos_disponiveis else 0

    with col_filtro:
        ano_selecionado = st.selectbox("📅 Selecione o Ano", anos_disponiveis, index=idx_ano)

    with col_titulo:
        st.title(f"📊 Dashboard Financeiro - {ano_selecionado}")
    
    # --- Filtragem dos Dados por Ano e Tipo ---
    df_rec_ano = df_mov[(df_mov['Tipo'] == 'Receita') & (df_mov['Data Realizado'].dt.year == ano_selecionado)].copy()
    df_pag_ano = df_mov[(df_mov['Tipo'] == 'Despesa') & (df_mov['Data Realizado'].dt.year == ano_selecionado)].copy()

    st.markdown("---") 

    # --- 1. KPIs Principais ---
    faturamento_total = df_rec_ano['Valor Realizado'].sum()
    gastos_totais = df_pag_ano['Valor Realizado'].sum()
    resultado = faturamento_total - gastos_totais
    
    inadimplencia_total = df_inad['Valor (R$)'].sum() if df_inad is not None else 0.0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Faturamento (Ano)", f"R$ {faturamento_total:,.2f}")
    col2.metric("Gastos Totais (Ano)", f"R$ {gastos_totais:,.2f}")
    col3.metric("Resultado (Ano)", f"R$ {resultado:,.2f}", delta_color="normal")
    col4.metric("Inadimplência (Total)", f"R$ {inadimplencia_total:,.2f}", delta_color="inverse")

    st.markdown("---")

    # --- 2. Evolução do Faturamento e Inadimplência ---
    col_evo1, col_evo2 = st.columns(2)
    
    with col_evo1:
        st.subheader("Evolução do Faturamento")
        if not df_rec_ano.empty:
            df_fat_mes = df_rec_ano.groupby(df_rec_ano['Data Realizado'].dt.to_period('M'))['Valor Realizado'].sum().reset_index()
            df_fat_mes['Data Realizado'] = df_fat_mes['Data Realizado'].dt.to_timestamp()
            df_fat_mes['Mes'] = df_fat_mes['Data Realizado'].dt.strftime('%B %Y')
            
            fig_fat = px.bar(df_fat_mes, x='Mes', y='Valor Realizado', text_auto='.2s')
            st.plotly_chart(fig_fat, use_container_width=True)
        else:
            st.info("Sem receitas registradas neste ano.")

    with col_evo2:
        st.subheader("Evolução da Inadimplência")
        if df_inad is not None:
            df_inad_ano = df_inad[df_inad['Últ. Pagamento'].dt.year == ano_selecionado]
            
            if not df_inad_ano.empty:
                df_inad_mes = df_inad_ano.groupby(df_inad_ano['Últ. Pagamento'].dt.to_period('M'))['Valor (R$)'].sum().reset_index()
                df_inad_mes['Últ. Pagamento'] = df_inad_mes['Últ. Pagamento'].dt.to_timestamp()
                df_inad_mes['Mes'] = df_inad_mes['Últ. Pagamento'].dt.strftime('%B %Y')
                fig_inad = px.line(df_inad_mes, x='Mes', y='Valor (R$)', markers=True, color_discrete_sequence=['red'])
                st.plotly_chart(fig_inad, use_container_width=True)
            else:
                st.info("Sem inadimplência registrada neste ano.")
        else:
            st.warning("Arquivo de Inadimplência não carregado.")

    # --- 3. Evolução do Caixa (Gráfico Combinado) ---
    st.subheader("Fluxo de Caixa (Entradas vs Saídas vs Saldo)")
    
    # Preparar dados mensais
    df_rec_ano['Mes'] = df_rec_ano['Data Realizado'].dt.to_period('M')
    df_pag_ano['Mes'] = df_pag_ano['Data Realizado'].dt.to_period('M')

    rec_mes = df_rec_ano.groupby('Mes')['Valor Realizado'].sum().reset_index().rename(columns={'Valor Realizado': 'Entradas'})
    pag_mes = df_pag_ano.groupby('Mes')['Valor Realizado'].sum().reset_index().rename(columns={'Valor Realizado': 'Saidas'})

    if not rec_mes.empty or not pag_mes.empty:
        df_fluxo = pd.merge(rec_mes, pag_mes, on='Mes', how='outer').fillna(0).sort_values('Mes')
        df_fluxo['Data'] = df_fluxo['Mes'].dt.to_timestamp()
        df_fluxo['Mes Formatado'] = df_fluxo['Data'].dt.strftime('%B %Y')
        
        df_fluxo['Saldo Mes'] = df_fluxo['Entradas'] - df_fluxo['Saidas']
        df_fluxo['Saldo Acumulado'] = df_fluxo['Saldo Mes'].cumsum()

        fig_combo = go.Figure()

        fig_combo.add_trace(go.Bar(
            x=df_fluxo['Mes Formatado'], y=df_fluxo['Entradas'], name='Entradas',
            marker_color='#2ecc71', opacity=0.7
        ))

        fig_combo.add_trace(go.Bar(
            x=df_fluxo['Mes Formatado'], y=df_fluxo['Saidas'], name='Saídas',
            marker_color='#e74c3c', opacity=0.7
        ))

        fig_combo.add_trace(go.Scatter(
            x=df_fluxo['Mes Formatado'], y=df_fluxo['Saldo Acumulado'], name='Saldo Acumulado',
            mode='lines+markers', marker_color='#2c3e50',
            line=dict(width=3), yaxis='y2'
        ))

        fig_combo.update_layout(
            xaxis_title='Mês', yaxis_title='Valor (R$)',
            barmode='group', hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis2=dict(title='Saldo Acumulado', overlaying='y', side='right')
        )

        st.plotly_chart(fig_combo, use_container_width=True)
    else:
        st.info("Sem dados suficientes para o fluxo de caixa.")

    st.divider()

    # --- 4. Análises de Gastos e Categorias ---
    col_cat1, col_cat2 = st.columns(2)

    with col_cat1:
        st.subheader("Top 10 Categorias (Receita)")
        if not df_rec_ano.empty:
            df_cat_rec = df_rec_ano.groupby('Categoria')['Valor Realizado'].sum().sort_values(ascending=True).tail(10)
            fig_cat_rec = px.bar(df_cat_rec, orientation='h', text_auto='.2s')
            st.plotly_chart(fig_cat_rec, use_container_width=True)
        else:
            st.info("Sem dados de receita.")

    with col_cat2:
        st.subheader("Distribuição de Gastos")
        if not df_pag_ano.empty:
            df_cat_pag = df_pag_ano.groupby('Categoria')['Valor Realizado'].sum().reset_index()
            # Agrupar categorias pequenas para limpar o gráfico
            total_pag = df_cat_pag['Valor Realizado'].sum()
            if total_pag > 0:
                limit = total_pag * 0.02 
                df_cat_pag.loc[df_cat_pag['Valor Realizado'] < limit, 'Categoria'] = 'Outros'
                fig_pie = px.pie(df_cat_pag, values='Valor Realizado', names='Categoria')
                st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Sem dados de despesa.")

    # --- 5. Análise Vertical ---
    st.subheader("Análise Vertical: Estrutura de Custos")
    
    # Filtros por palavras-chave comuns
    impostos = df_pag_ano[df_pag_ano['Categoria'].str.contains('Imposto|DAS|DARF|ISS|PIS|COFINS|Tributo', case=False, na=False)]['Valor Realizado'].sum()
    folha = df_pag_ano[df_pag_ano['Categoria'].str.contains('Folha|Salário|Pró-labore|Pessoal|INSS|FGTS', case=False, na=False)]['Valor Realizado'].sum()
    terceiros = df_pag_ano[df_pag_ano['Categoria'].str.contains('Terceir|Serviço|PJ|Consultoria', case=False, na=False)]['Valor Realizado'].sum()
    
    dados_analise = {
        'Grupo': ['Impostos', 'Folha / Pessoal', 'Terceirização', 'Margem Bruta (Aprox)'],
        'Valor (R$)': [impostos, folha, terceiros, faturamento_total - (impostos + folha + terceiros)],
    }
    df_analise = pd.DataFrame(dados_analise)
    
    if faturamento_total > 0:
        df_analise['% do Faturamento'] = (df_analise['Valor (R$)'] / faturamento_total) * 100
    else:
        df_analise['% do Faturamento'] = 0

    col_av1, col_av2 = st.columns([1, 2])
    with col_av1:
        st.dataframe(df_analise.style.format({'Valor (R$)': 'R$ {:,.2f}', '% do Faturamento': '{:.1f}%'}), use_container_width=True)
    with col_av2:
        fig_av = px.bar(df_analise, x='Grupo', y='% do Faturamento', text_auto='.1f', title="Peso sobre Faturamento")
        st.plotly_chart(fig_av, use_container_width=True)

else:
    st.info("Por favor, faça o upload do arquivo 'movimentacoes-financeiras.csv' para visualizar o dashboard.")