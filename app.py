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

    # Função auxiliar para tratar datas
    def tratar_datas(df, colunas):
        for col in colunas:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
        return df
    
    # Função auxiliar INTELIGENTE para tratar valores
    def tratar_valor(series):
        if pd.api.types.is_numeric_dtype(series):
            return series.fillna(0)
        return pd.to_numeric(series.astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False), errors='coerce').fillna(0)

    try:
        # Carregar Movimentações
        if file_mov is not None:
            df_mov = pd.read_csv(file_mov)
        else:
            try:
                df_mov = pd.read_csv("movimentacoes-financeiras.csv")
            except FileNotFoundError:
                pass
        
        if df_mov is not None:
            # Filtro: Remover Transferências
            if 'Transferência' in df_mov.columns:
                df_mov = df_mov[df_mov['Transferência'] != 'Sim'] 
            
            df_mov = tratar_datas(df_mov, ['Data Realizado', 'Vencimento', 'Competência'])
            
            cols_valor = ['Valor Realizado', 'Valor (R$)']
            for col in cols_valor:
                if col in df_mov.columns:
                     df_mov[col] = tratar_valor(df_mov[col])

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
                df_inad['Valor (R$)'] = tratar_valor(df_inad['Valor (R$)'])

        # Opcionais
        if file_receber is not None:
            df_receber = pd.read_csv(file_receber)
        if file_pagar is not None:
            df_pagar = pd.read_csv(file_pagar)

    except Exception as e:
        st.error(f"Erro ao carregar arquivos: {e}")
        return None, None, None, None

    return df_receber, df_pagar, df_mov, df_inad

# Carrega os dados
df_receber, df_pagar, df_mov, df_inad = carregar_dados(uploaded_receber, uploaded_pagar, uploaded_mov, uploaded_inad)

if df_mov is not None:
    
    # --- Layout de Filtros (Topo) ---
    col_titulo, col_filtros = st.columns([1, 2])
    
    with col_titulo:
        st.title("📊 Dashboard")

    with col_filtros:
        c_ano, c_mes, c_conta = st.columns(3)
        
        # Filtro de Ano
        anos_disponiveis = sorted(df_mov['Data Realizado'].dt.year.dropna().unique().astype(int))
        if not anos_disponiveis:
            st.warning("Sem datas válidas.")
            st.stop()
        
        idx_ano = len(anos_disponiveis)-1
        with c_ano:
            ano_selecionado = st.selectbox("Ano", anos_disponiveis, index=idx_ano)

        # Filtro de Mês
        meses_nomes = {
            0: 'Todos', 1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
            7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
        }
        with c_mes:
            mes_nome_selecionado = st.selectbox("Mês", list(meses_nomes.values()), index=0)
            # Encontrar o número do mês baseado no nome
            mes_num_selecionado = [k for k, v in meses_nomes.items() if v == mes_nome_selecionado][0]

        # Filtro de Conta Financeira
        with c_conta:
            contas_disponiveis = sorted(df_mov['Nome da Conta Financeira'].astype(str).unique())
            contas_selecionadas = st.multiselect("Conta Financeira", contas_disponiveis, placeholder="Todas")

    # --- Aplicação dos Filtros ---
    
    # 1. Filtro Global de Movimentações (Ano, Mês e Conta)
    df_mov_filtrado = df_mov[df_mov['Data Realizado'].dt.year == ano_selecionado].copy()
    
    if mes_num_selecionado != 0:
        df_mov_filtrado = df_mov_filtrado[df_mov_filtrado['Data Realizado'].dt.month == mes_num_selecionado]
    
    if contas_selecionadas:
        df_mov_filtrado = df_mov_filtrado[df_mov_filtrado['Nome da Conta Financeira'].isin(contas_selecionadas)]

    # Separação Receita/Despesa (Base filtrada)
    df_rec_filtrado = df_mov_filtrado[df_mov_filtrado['Tipo'] == 'Receita']
    df_pag_filtrado = df_mov_filtrado[df_mov_filtrado['Tipo'] == 'Despesa']
    
    # 2. Filtro de Inadimplência (Ano e Mês apenas - Tabela Inadimplência não tem conta financeira)
    valor_inadimplencia = 0.0
    df_inad_filtrado = pd.DataFrame()
    
    if df_inad is not None:
        df_inad_filtrado = df_inad[df_inad['Últ. Pagamento'].dt.year == ano_selecionado].copy()
        if mes_num_selecionado != 0:
            df_inad_filtrado = df_inad_filtrado[df_inad_filtrado['Últ. Pagamento'].dt.month == mes_num_selecionado]
        valor_inadimplencia = df_inad_filtrado['Valor (R$)'].sum()

    st.markdown("---") 

    # --- 1. KPIs Principais ---
    faturamento_total = df_rec_filtrado['Valor Realizado'].sum()
    gastos_totais = df_pag_filtrado['Valor Realizado'].sum()
    resultado = faturamento_total - gastos_totais

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(f"Faturamento ({mes_nome_selecionado})", f"R$ {faturamento_total:,.2f}")
    col2.metric(f"Gastos Totais ({mes_nome_selecionado})", f"R$ {gastos_totais:,.2f}")
    col3.metric("Resultado", f"R$ {resultado:,.2f}", delta_color="normal")
    col4.metric("Inadimplência", f"R$ {valor_inadimplencia:,.2f}", delta_color="inverse")

    st.markdown("---")

    # --- 2. Evolução e Gráficos ---
    # Se um mês específico for selecionado, os gráficos de "evolução mensal" mostrarão apenas aquele mês.
    
    col_evo1, col_evo2 = st.columns(2)
    
    with col_evo1:
        st.subheader("Faturamento (Detalhe Temporal)")
        if not df_rec_filtrado.empty:
            df_fat_mes = df_rec_filtrado.groupby(df_rec_filtrado['Data Realizado'].dt.to_period('M'))['Valor Realizado'].sum().reset_index()
            df_fat_mes['Data Realizado'] = df_fat_mes['Data Realizado'].dt.to_timestamp()
            df_fat_mes['Mes'] = df_fat_mes['Data Realizado'].dt.strftime('%B %Y')
            
            fig_fat = px.bar(df_fat_mes, x='Mes', y='Valor Realizado', text_auto='.2s')
            st.plotly_chart(fig_fat, use_container_width=True)
        else:
            st.info("Sem receitas para os filtros selecionados.")

    with col_evo2:
        st.subheader("Inadimplência (Detalhe Temporal)")
        if not df_inad_filtrado.empty:
            df_inad_mes = df_inad_filtrado.groupby(df_inad_filtrado['Últ. Pagamento'].dt.to_period('M'))['Valor (R$)'].sum().reset_index()
            df_inad_mes['Últ. Pagamento'] = df_inad_mes['Últ. Pagamento'].dt.to_timestamp()
            df_inad_mes['Mes'] = df_inad_mes['Últ. Pagamento'].dt.strftime('%B %Y')
            fig_inad = px.line(df_inad_mes, x='Mes', y='Valor (R$)', markers=True, color_discrete_sequence=['red'])
            st.plotly_chart(fig_inad, use_container_width=True)
        else:
            st.info("Sem inadimplência para os filtros selecionados.")

    # --- 3. Fluxo de Caixa ---
    st.subheader("Fluxo de Caixa")
    
    df_rec_filtrado['Mes_Periodo'] = df_rec_filtrado['Data Realizado'].dt.to_period('M')
    df_pag_filtrado['Mes_Periodo'] = df_pag_filtrado['Data Realizado'].dt.to_period('M')

    rec_mes = df_rec_filtrado.groupby('Mes_Periodo')['Valor Realizado'].sum().reset_index().rename(columns={'Valor Realizado': 'Entradas'})
    pag_mes = df_pag_filtrado.groupby('Mes_Periodo')['Valor Realizado'].sum().reset_index().rename(columns={'Valor Realizado': 'Saidas'})

    if not rec_mes.empty or not pag_mes.empty:
        df_fluxo = pd.merge(rec_mes, pag_mes, on='Mes_Periodo', how='outer').fillna(0).sort_values('Mes_Periodo')
        df_fluxo['Data'] = df_fluxo['Mes_Periodo'].dt.to_timestamp()
        df_fluxo['Mes Formatado'] = df_fluxo['Data'].dt.strftime('%B %Y')
        
        df_fluxo['Saldo Mes'] = df_fluxo['Entradas'] - df_fluxo['Saidas']
        # O Saldo Acumulado aqui é relativo apenas ao período filtrado
        df_fluxo['Saldo Acumulado'] = df_fluxo['Saldo Mes'].cumsum()

        fig_combo = go.Figure()
        fig_combo.add_trace(go.Bar(x=df_fluxo['Mes Formatado'], y=df_fluxo['Entradas'], name='Entradas', marker_color='#2ecc71', opacity=0.7))
        fig_combo.add_trace(go.Bar(x=df_fluxo['Mes Formatado'], y=df_fluxo['Saidas'], name='Saídas', marker_color='#e74c3c', opacity=0.7))
        fig_combo.add_trace(go.Scatter(x=df_fluxo['Mes Formatado'], y=df_fluxo['Saldo Acumulado'], name='Saldo Acumulado', mode='lines+markers', marker_color='#2c3e50', line=dict(width=3), yaxis='y2'))

        fig_combo.update_layout(
            barmode='group', hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis2=dict(title='Saldo Acumulado', overlaying='y', side='right')
        )
        st.plotly_chart(fig_combo, use_container_width=True)
    else:
        st.info("Sem dados para exibir no fluxo de caixa.")

    st.divider()

    # --- 4. Análises de Categoria ---
    col_cat1, col_cat2 = st.columns(2)

    with col_cat1:
        st.subheader("Top Categorias (Receita)")
        if not df_rec_filtrado.empty:
            df_cat_rec = df_rec_filtrado.groupby('Categoria')['Valor Realizado'].sum().sort_values(ascending=True).tail(10)
            fig_cat_rec = px.bar(df_cat_rec, orientation='h', text_auto='.2s')
            st.plotly_chart(fig_cat_rec, use_container_width=True)
        else:
            st.info("Sem dados.")

    with col_cat2:
        st.subheader("Distribuição de Gastos")
        if not df_pag_filtrado.empty:
            df_cat_pag = df_pag_filtrado.groupby('Categoria')['Valor Realizado'].sum().reset_index()
            total_pag = df_cat_pag['Valor Realizado'].sum()
            if total_pag > 0:
                limit = total_pag * 0.02 
                df_cat_pag.loc[df_cat_pag['Valor Realizado'] < limit, 'Categoria'] = 'Outros'
                fig_pie = px.pie(df_cat_pag, values='Valor Realizado', names='Categoria')
                st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Sem dados.")

    # --- 5. Análise Vertical ---
    st.subheader("Análise Vertical")
    
    impostos = df_pag_filtrado[df_pag_filtrado['Categoria'].str.contains('Imposto|DAS|DARF|ISS|PIS|COFINS|Tributo', case=False, na=False)]['Valor Realizado'].sum()
    folha = df_pag_filtrado[df_pag_filtrado['Categoria'].str.contains('Folha|Salário|Pró-labore|Pessoal|INSS|FGTS', case=False, na=False)]['Valor Realizado'].sum()
    terceiros = df_pag_filtrado[df_pag_filtrado['Categoria'].str.contains('Terceir|Serviço|PJ|Consultoria', case=False, na=False)]['Valor Realizado'].sum()
    
    dados_analise = {
        'Grupo': ['Impostos', 'Folha / Pessoal', 'Terceirização', 'Margem Bruta (Aprox)'],
        'Valor (R$)': [impostos, folha, terceiros, faturamento_total - (impostos + folha + terceiros)],
    }
    df_analise = pd.DataFrame(dados_analise)
    df_analise['% do Faturamento'] = (df_analise['Valor (R$)'] / faturamento_total * 100) if faturamento_total > 0 else 0

    col_av1, col_av2 = st.columns([1, 2])
    with col_av1:
        st.dataframe(df_analise.style.format({'Valor (R$)': 'R$ {:,.2f}', '% do Faturamento': '{:.1f}%'}), use_container_width=True)
    with col_av2:
        fig_av = px.bar(df_analise, x='Grupo', y='% do Faturamento', text_auto='.1f')
        st.plotly_chart(fig_av, use_container_width=True)

else:
    st.info("Por favor, faça o upload do arquivo 'movimentacoes-financeiras.csv'.")