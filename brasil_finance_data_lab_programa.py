import pandas as pd
import requests
import matplotlib.pyplot as plt
import time

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# 1. FUNÇÃO PARA BUSCAR INDICADORES

def buscar_indicador(codigo, inicio, fim):
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"

    for tentativa in range(1, 3):
        try:
            print(f"Consultando série {codigo} - tentativa {tentativa}")

            resposta = requests.get(
                url,
                params={
                    "formato": "json",
                    "dataInicial": inicio,
                    "dataFinal": fim
                },
                timeout=60
            )

            resposta.raise_for_status()

            dados = resposta.json()
            tabela = pd.DataFrame(dados)

            print(f"Série {codigo} recebida com sucesso!")
            return tabela

        except requests.exceptions.Timeout:
            print(f"Tempo esgotado na série {codigo}.")

            if tentativa == 2:
                raise

            print("Aguardando 5 segundos...")
            time.sleep(5)


def preparar_dados(tabela):
    tabela = tabela.copy()

    tabela["data"] = pd.to_datetime(
        tabela["data"], dayfirst=True
    )

    tabela["valor"] = pd.to_numeric(tabela["valor"])
    tabela["mes"] = tabela["data"].dt.to_period("M")

    return tabela

# 2. CONFIGURAÇÕES

inicio = "01/01/2021"

hoje = datetime.now(ZoneInfo("America/Sao_Paulo"))
primeiro_dia_mes = hoje.replace(day=1)
ultimo_dia_mes_anterior = primeiro_dia_mes - timedelta(days=1)

fim = ultimo_dia_mes_anterior.strftime("%d/%m/%Y")

print("Período solicitado:", inicio, "até", fim)


# 3. COLETAR DADOS

ipca = buscar_indicador(433, inicio, fim)
selic = buscar_indicador(4390, inicio, fim)

print("IPCA recebido:", len(ipca), "registros")
print("Selic recebida:", len(selic), "registros")


# 4. PREPARAR AS TABELAS

ipca = preparar_dados(ipca)
selic = preparar_dados(selic)

ipca = ipca.rename(columns={"valor": "ipca"})
selic = selic.rename(columns={"valor": "selic"})


# 5. COMBINAR OS INDICADORES

df_completo = pd.merge(
    ipca[["mes", "ipca"]],
    selic[["mes", "selic"]],
    on="mes",
    how="inner",
    validate="one_to_one"
).sort_values("mes")

if df_completo.empty:
    raise ValueError("Nenhum mês em comum foi encontrado.")


# 6. VERIFICAR O PERÍODO

primeiro_mes = df_completo["mes"].min()
ultimo_mes = df_completo["mes"].max()

print("Primeiro mês:", primeiro_mes)
print("Último mês:", ultimo_mes)
print("Total de meses:", len(df_completo))


# 7. ANALISAR OS DADOS

maior_ipca = df_completo.loc[df_completo["ipca"].idxmax()]
maior_selic = df_completo.loc[df_completo["selic"].idxmax()]


# 8. EXPORTAR CSV

df_completo.to_csv(
    "indicadores_brasil.csv",
    index=False,
    sep=";",
    decimal=","
)


# 9. GERAR RELATÓRIO

relatorio = f"""
=== BRASIL FINANCE DATA LAB ===
Relatorio Economico - Versao 0.2

Periodo: {primeiro_mes} ate {ultimo_mes}
Total de meses: {len(df_completo)}

Maior IPCA mensal:
{maior_ipca["mes"]}: {maior_ipca["ipca"]:.2f}%

Maior Selic mensal:
{maior_selic["mes"]}: {maior_selic["selic"]:.2f}%

Fonte: Banco Central do Brasil
Series SGS: 433 e 4390
"""

with open("relatorio_brasil.txt", "w", encoding="utf-8") as arquivo:
    arquivo.write(relatorio)


# 10. GERAR GRÁFICO

plt.figure(figsize=(12, 5))

datas = df_completo["mes"].dt.to_timestamp()

plt.plot(datas, df_completo["ipca"], label="IPCA mensal")
plt.plot(datas, df_completo["selic"], label="Selic mensal")

plt.title(f"IPCA x Selic - Brasil ({primeiro_mes} a {ultimo_mes})")
plt.xlabel("Data")
plt.ylabel("Taxa mensal (%)")

plt.legend()
plt.grid(True)
plt.tight_layout()

plt.savefig("grafico_indicadores.png", dpi=150)
plt.show()


# 11. MOSTRAR RESULTADOS

print(relatorio)
print("Arquivos gerados com sucesso!")
