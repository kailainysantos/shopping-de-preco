from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import random

# Configurar o navegador
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
navegador = webdriver.Chrome(options=options)

# Ler lista de EANs de um arquivo CSV
try:
    ean_df = pd.read_csv("ean_list.csv")
except FileNotFoundError:
    print("Erro: Crie um arquivo 'ean_list.csv' com colunas 'ean' e 'termo_mercado_livre'")
    exit()

# Dicionário para armazenar resultados
resultados = []

# Função para buscar preços
def buscar_precos(site, url_base, seletor_preco, termo, ean):
    navegador.get(url_base.format(termo))
    try:
        WebDriverWait(navegador, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, seletor_preco))
        )
        if site == "Mercado Livre":
            itens = navegador.find_elements(By.CSS_SELECTOR, "li.ui-search-layout__item")
            precos = []
            for item in itens[:5]:
                try:
                    texto_item = item.text.lower()
                    if str(ean) in texto_item:
                        preco = item.find_element(By.CSS_SELECTOR, seletor_preco).text
                        precos.append(preco)
                except:
                    continue
        else:
            precos = [elem.text for elem in navegador.find_elements(By.CSS_SELECTOR, seletor_preco)[:5]]
        print(f"{site} (EAN {ean}): Encontrados {len(precos)} resultados")
        return precos if precos else ["Nenhum preço encontrado"]
    except Exception as e:
        print(f"{site} (EAN {ean}): Erro ao buscar preços - {str(e)}")
        return ["Erro ao buscar preços"]

# Sites e seletores
sites = {
    "Mercado Livre": {
        "url": "https://www.mercadolivre.com.br/search?query={}",
        "seletor": "span.andes-money-amount__fraction"
    },
    "Amazon": {
        "url": "https://www.amazon.com.br/s?k={}",
        "seletor": "span.a-price"
    },
    "Magazine Luiza": {
        "url": "https://www.magazineluiza.com.br/busca/{}",
        "seletor": "span.sc-kpDqfm.eCPtRw"
    }
}

# Buscar preços para cada EAN
for index, row in ean_df.iterrows():
    ean = str(row["ean"])
    termo_ml = row["termo_mercado_livre"]
    print(f"Buscando preços para EAN {ean}...")
    
    ean_resultados = {"EAN": ean, "Produto": termo_ml}
    for site, info in sites.items():
        termo = termo_ml if site == "Mercado Livre" else ean
        precos = buscar_precos(site, info["url"], info["seletor"], termo, ean)
        ean_resultados[site] = ", ".join(precos)
        time.sleep(random.uniform(1, 3))  # Pausa aleatória para evitar bloqueios
    
    resultados.append(ean_resultados)

# Fechar o navegador
navegador.quit()

# Salvar resultados em uma planilha Excel
resultados_df = pd.DataFrame(resultados)
resultados_df.to_excel("precos_300_produtos.xlsx", index=False)
print("Preços salvos em 'precos_300_produtos.xlsx'")