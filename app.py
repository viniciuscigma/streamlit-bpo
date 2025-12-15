import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Dashboard de Dados", layout="wide")

st.title("📊 Dashboard Analítico")

# 1. Carregamento dos dados com Cache (para performance)
@st.cache_data
def carregar_dados():
    # Se o CSV for separado por ponto e vírgula, use sep=';'
    return pd.read_csv("Contas a pagar.csv")

try:
    df = carregar_dados()
    
    # Mostra os dados brutos (opcional)
    if st.checkbox("Mostrar dados brutos"):
        st.dataframe(df)

    # 2. Realizando Cálculos
    # Exemplo: Criando uma coluna de 'Lucro' (ajuste conforme suas colunas reais)
    # Supondo que você tenha colunas 'Vendas' e 'Custos'
    # df['Lucro'] = df['Vendas'] - df['Custos'] 
    
    # Exemplo genérico: Agrupamento
    st.subheader("Análise Gráfica")
    
    # Seus dados precisam ter colunas numéricas para plotar. 
    # Ajuste 'Categoria' e 'Valor' para os nomes reais das suas colunas no CSV.
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de Barras
        fig_bar = px.bar(df, x=df.columns[0], y=df.columns[1], title="Gráfico de Barras")
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with col2:
        # Gráfico de Pizza ou Linha
        fig_line = px.line(df, x=df.columns[0], y=df.columns[1], title="Evolução Temporal")
        st.plotly_chart(fig_line, use_container_width=True)

except FileNotFoundError:
    st.error("Arquivo 'dados.csv' não encontrado. Certifique-se de que ele está na mesma pasta.")
except Exception as e:
    st.error(f"Erro ao processar dados: {e}")