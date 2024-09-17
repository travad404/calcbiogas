import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Funções para os cálculos
def calcular_separacao(total_residuo, percentuais):
    return total_residuo * np.array(percentuais)

def calcular_biogas(quantidade, fator_biogas):
    return quantidade * fator_biogas

# Configurações iniciais
percentuais_separacao = [0.5557, 0.1355, 0.0829, 0.02, 0.0209, 0.0067]  # Manual

fator_biogas_poda = 0.460  # Fator de geração de biogás por tonelada de podas
fator_biogas_organico = 0.215  # Fator de geração de biogás para orgânicos
fator_biogas_papel = 0.358  # Fator de geração de biogás para papel/papelão

# Interface do Streamlit
st.title("Análise de Resíduos Sólidos")

# Carregar o arquivo Excel
uploaded_file = st.file_uploader("Escolha o arquivo Excel", type="xlsx")
if uploaded_file is not None:
    try:
        # Ler o arquivo Excel
        df = pd.read_excel(uploaded_file, engine='openpyxl')

        # Exibir todos os nomes de colunas para verificar a estrutura
        st.write("Nomes das Colunas no Arquivo:")
        st.write(df.columns.tolist())

        # Pedir ao usuário para selecionar as colunas corretas
        cols_municipio = st.selectbox("Selecione a coluna para Município:", df.columns)
        cols_total = st.selectbox("Selecione a coluna para Total de Resíduos:", df.columns)
        cols_dom_pub = st.selectbox("Selecione a coluna para Resíduos Dom+Pub:", df.columns)
        cols_podas = st.selectbox("Selecione a coluna para Resíduos de Podas:", df.columns)
        
        # Filtrando as colunas escolhidas
        df_filtered = df[[cols_municipio, cols_total, cols_dom_pub, cols_podas]]

        # Convertendo colunas para numérico, se necessário
        df_filtered[cols_total] = pd.to_numeric(df_filtered[cols_total], errors='coerce')
        df_filtered[cols_dom_pub] = pd.to_numeric(df_filtered[cols_dom_pub], errors='coerce')
        df_filtered[cols_podas] = pd.to_numeric(df_filtered[cols_podas], errors='coerce')

        # Exibir os dados filtrados
        st.write("Dados Filtrados:")
        st.write(df_filtered)

        # Separação dos resíduos domiciliares + públicos
        total_residuo_dom_pub = df_filtered[cols_dom_pub].sum()
        separacoes = calcular_separacao(total_residuo_dom_pub, percentuais_separacao)
        
        # Resultados de separação em tabela
        st.write("Resultados da Separação Manual (em toneladas):")
        separacao_df = pd.DataFrame([separacoes], columns=['Orgânico', 'Plástico', 'Papel/Papelão', 'Metal', 'Vidro', 'Outros'])
        st.table(separacao_df)

        # Cálculo da geração de biogás por podas
        total_podas = df_filtered[cols_podas].sum()
        biogas_podas = calcular_biogas(total_podas, fator_biogas_poda)
        st.write(f"Total de biogás gerado por podas: {biogas_podas} m³")

        # Cálculo da geração de biogás
        biogas_organico = calcular_biogas(separacoes[0], fator_biogas_organico)
        biogas_papel = calcular_biogas(separacoes[2], fator_biogas_papel)
        biogas_total = biogas_organico + biogas_papel + biogas_podas
        
        biogas_detalhado = {
            'Orgânico': biogas_organico,
            'Papel/Papelão': biogas_papel,
            'Podas': biogas_podas,
            'Total': biogas_total
        }
        
        # Exibir resultados de biogás
        st.write("Geração de Biogás (em m³):")
        biogas_df = pd.DataFrame([biogas_detalhado])
        st.table(biogas_df)

        # Geração de biogás detalhada (por fonte)
        st.write("Geração de Biogás Detalhada (por fonte):")
        st.table(biogas_df.drop(columns=['Total']))

        # Gráficos de pizza para composição de biogás por fonte
        st.write("Composição de Biogás")
        fig, ax = plt.subplots()
        ax.pie(
            biogas_df.loc[0, ['Orgânico', 'Papel/Papelão', 'Podas']],
            labels=['Orgânico', 'Papel/Papelão', 'Podas'],
            autopct='%1.1f%%',
            startangle=140
        )
        ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        st.pyplot(fig)

        # Input do usuário para fator de purificação de biogás para biometano
        purificacao = st.number_input("Digite o fator de purificação de biogás para biometano (%):", min_value=0.0, max_value=100.0, value=50.0)
        fator_purificacao = purificacao / 100  # Convertendo para decimal

        # Cálculo de biometano a partir do biogás usando o fator de purificação
        biometano_detalhado = {k: v * fator_purificacao for k, v in biogas_detalhado.items() if k != 'Total'}
        biometano_detalhado['Total'] = sum(biometano_detalhado.values())


        st.write("Geração de Biometano após Purificação (em m³):")
        st.table(pd.DataFrame([biometano_detalhado]))

        # Agregação de resíduos "Dom+Pub" por município
        df_municipios = df_filtered.groupby(cols_municipio)[cols_dom_pub].sum().reset_index()
        df_municipios.columns = ['Município', 'Dom+Pub Total']
        st.write("Total de Resíduos Dom+Pub por Município:")
        st.table(df_municipios)

        # Selecionar os 7 municípios com maior volume de resíduos "Dom+Pub" e agrupar o restante como "Outros"
        top7_dom_pub = df_municipios.nlargest(7, 'Dom+Pub Total')
        outros_dom_pub = df_municipios[~df_municipios.isin(top7_dom_pub)].sum(numeric_only=True)
        outros_dom_pub['Município'] = 'Outros'

        # Combinar os dados
        df_dom_pub_agrupados = pd.concat([top7_dom_pub, pd.DataFrame([outros_dom_pub])], ignore_index=True)

        # Gráfico de pizza para total de resíduos "Dom+Pub" por município
        st.write("Distribuição de Resíduos Dom+Pub por Município:")
        fig, ax = plt.subplots()
        ax.pie(
            df_dom_pub_agrupados['Dom+Pub Total'],
            labels=df_dom_pub_agrupados['Município'],
            autopct='%1.1f%%',
            startangle=140
        )
        ax.axis('equal')
        st.pyplot(fig)

        # Agregação de resíduos "Podas" por município
        df_podas_municipios = df_filtered.groupby(cols_municipio)[cols_podas].sum().reset_index()
        df_podas_municipios.columns = ['Município', 'Podas Total']
        st.write("Total de Resíduos de Podas por Município:")
        st.table(df_podas_municipios)

        # Selecionar os 7 municípios com maior volume de resíduos "Podas" e agrupar o restante como "Outros"
        top7_podas = df_podas_municipios.nlargest(7, 'Podas Total')
        outros_podas = df_podas_municipios[~df_podas_municipios.isin(top7_podas)].sum(numeric_only=True)
        outros_podas['Município'] = 'Outros'

        # Combinar os dados
        df_podas_agrupados = pd.concat([top7_podas, pd.DataFrame([outros_podas])], ignore_index=True)

        # Gráfico de pizza para total de resíduos "Podas" por município
        st.write("Distribuição de Resíduos de Podas por Município:")
        fig, ax = plt.subplots()
        ax.pie(
            df_podas_agrupados['Podas Total'],
            labels=df_podas_agrupados['Município'],
            autopct='%1.1f%%',
            startangle=140
        )
        ax.axis('equal')
        st.pyplot(fig)

    except Exception as e:
        st.error(f"Ocorreu um erro ao processar o arquivo: {e}")
