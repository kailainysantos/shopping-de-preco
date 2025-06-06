from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException # Importa TimeoutException corretamente
import pandas as pd
import time
import random
import re # Importa regex para limpeza de preços

# --- Configuração do Navegador ---
options = webdriver.ChromeOptions()
options.add_argument("--headless") # Executa o navegador em modo invisível (sem interface gráfica)
options.add_argument("--no-sandbox") # Necessário para alguns ambientes (ex: Docker)
options.add_argument("--disable-dev-shm-usage") # Otimização de memória para alguns ambientes
options.add_argument("--window-size=1920,1080") # Define um tamanho de janela consistente para renderização
navegador = webdriver.Chrome(options=options)

# --- Carregamento da Lista de EANs do Arquivo CSV ---
# O bloco try-except abaixo tenta ler o arquivo CSV com diferentes codificações
# para evitar o erro 'UnicodeDecodeError'.
try:
    try:
        # Tenta ler com a codificação UTF-8 primeiro (codificação padrão e mais comum)
        ean_df = pd.read_csv("ean_list.csv", encoding='utf-8')
    except UnicodeDecodeError:
        # Se UTF-8 falhar, tenta com latin-1 (comum em arquivos CSV brasileiros e de Windows)
        print("UTF-8 decoding failed, trying latin-1 encoding for 'ean_list.csv'...")
        ean_df = pd.read_csv("ean_list.csv", encoding='latin-1')
    except Exception as e:
        # Captura qualquer outro erro que possa ocorrer durante a leitura do CSV
        print(f"Erro inesperado ao ler o arquivo 'ean_list.csv': {e}")
        exit()

    # Verifica se as colunas essenciais existem no DataFrame
    if 'ean' not in ean_df.columns or 'termo_mercado_livre' not in ean_df.columns:
        raise ValueError("O arquivo 'ean_list.csv' deve conter as colunas 'ean' e 'termo_mercado_livre'.")

except FileNotFoundError:
    print("Erro: O arquivo 'ean_list.csv' não foi encontrado. Por favor, crie-o na mesma pasta do script com as colunas 'ean' e 'termo_mercado_livre'.")
    exit()
except ValueError as e:
    print(f"Erro na estrutura do arquivo CSV: {e}")
    exit()

# Lista para armazenar todos os resultados da busca de preços
all_results = []

# --- Função Auxiliar para Limpeza e Padronização de Preços ---
def clean_price(price_text):
    """
    Limpa e padroniza o texto de um preço, convertendo-o para um número float.
    Lida com símbolos de moeda, espaços e diferentes separadores decimais (vírgula/ponto).
    Retorna float ou None se não conseguir converter.
    """
    if not isinstance(price_text, str):
        return None
    # Remove símbolos de moeda e caracteres não numéricos, exceto vírgula e ponto
    cleaned_text = re.sub(r'[^\d,.]', '', price_text)
    # Substitui vírgula por ponto para permitir a conversão para float
    cleaned_text = cleaned_text.replace(',', '.')
    # Lida com números formatados como "1.234.567,89" (remove pontos de milhar)
    # Verifica se há mais de um ponto E o último segmento tem 2 dígitos (prováveis centavos)
    if cleaned_text.count('.') > 1 and len(cleaned_text.split('.')[-1]) == 2:
        parts = cleaned_text.split('.')
        cleaned_text = ''.join(parts[:-1]) + '.' + parts[-1]
    elif cleaned_text.count('.') > 1: # Se mais de um ponto e não é o caso de centavos, remove todos os pontos
        cleaned_text = cleaned_text.replace('.', '')

    try:
        return float(cleaned_text)
    except ValueError:
        return None

# --- Função Principal para Buscar Preços em Diferentes Sites ---
def find_prices(site_name, base_url, price_selector, search_term, ean):
    """
    Navega até a URL do site, aguarda os elementos de preço e os extrai.
    Possui lógica específica para o Mercado Livre para filtrar por EAN na descrição do produto.
    """
    full_url = base_url.format(search_term)
    print(f"  Acessando {site_name} para '{search_term}' (EAN: {ean})...")
    navegador.get(full_url)

    prices_found = []
    try:
        # Aguarda a presença de *todos* os elementos que contêm o preço na página
        WebDriverWait(navegador, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, price_selector))
        )

        if site_name == "Mercado Livre":
            # Para o Mercado Livre, precisamos de uma lógica mais específica.
            # Buscamos os itens da lista de resultados e filtramos por EAN no texto.
            items = navegador.find_elements(By.CSS_SELECTOR, "li.ui-search-layout__item")
            for item in items[:10]: # Verifica os primeiros 10 itens para aumentar a chance de encontrar
                try:
                    item_text = item.text.lower()
                    # Verifica se o EAN (convertido para string) está no texto do item
                    if str(ean) in item_text:
                        # Tenta encontrar a parte inteira e os centavos do preço
                        price_whole_element = item.find_element(By.CSS_SELECTOR, "span.andes-money-amount__fraction")
                        price_whole = price_whole_element.text
                        cents_element = item.find_elements(By.CSS_SELECTOR, "span.andes-money-amount__cents")
                        price_cents = cents_element[0].text if cents_element else "00"
                        full_price_text = f"{price_whole},{price_cents}"
                        
                        cleaned_price_value = clean_price(full_price_text)
                        if cleaned_price_value is not None:
                            prices_found.append(cleaned_price_value)
                except Exception as e_item_price:
                    # Se houver erro ao extrair o preço de um item específico, apenas ignora
                    pass
        else:
            # Lógica generalizada para Amazon e Magazine Luiza: extrai os preços diretamente
            price_elements = navegador.find_elements(By.CSS_SELECTOR, price_selector)
            for elem in price_elements[:5]: # Pega os 5 primeiros preços encontrados
                cleaned_price_value = clean_price(elem.text)
                if cleaned_price_value is not None:
                    prices_found.append(cleaned_price_value)

        print(f"  {site_name} (EAN {ean}): Encontrados {len(prices_found)} preços válidos.")
        # Retorna os 3 menores preços encontrados (já limpos e em float)
        return sorted(prices_found)[:3] if prices_found else ["Não encontrado"]
    
    except TimeoutException: # Aqui é a correção do AttributeError
        print(f"  {site_name} (EAN {ean}): Tempo esgotado esperando pelos preços. O seletor '{price_selector}' não foi encontrado.")
        return ["Não encontrado"]
    except Exception as e:
        print(f"  {site_name} (EAN {ean}): Erro geral ao buscar preços - {str(e)}")
        return ["Erro na busca"]

# --- Configurações dos Sites e Seletores ---
sites = {
    "Mercado Livre": {
        "url": "https://www.mercadolivre.com.br/search?query={}",
        "seletor": "span.andes-money-amount__fraction"
    },
    "Amazon": {
        "url": "https://www.amazon.com.br/s?k={}",
        "seletor": "span.a-price-whole, span.a-price-fraction"
    },
    "Magazine Luiza": {
        "url": "https://www.magazineluiza.com.br/busca/{}",
        "seletor": "p[data-testid='price-value']"
    }
}

# --- Loop Principal para Buscar Preços para Cada EAN ---
for index, row in ean_df.iterrows():
    # Assegura que 'ean' e 'termo_mercado_livre' são strings, mesmo que pandas leia como NaN
    ean = str(row["ean"]) if pd.notna(row["ean"]) else ""
    termo_ml = str(row["termo_mercado_livre"]) if pd.notna(row["termo_mercado_livre"]) else ""

    if not ean: # Se o EAN estiver vazio ou inválido, pula essa linha
        print(f"Aviso: Linha {index+2} no CSV tem EAN inválido/vazio. Pulando...")
        continue

    print(f"\n--- Processando EAN: {ean} (Produto: {termo_ml}) ---")

    ean_results = {"EAN": ean, "Produto": termo_ml}
    for site, info in sites.items():
        search_term = termo_ml if site == "Mercado Livre" else ean
        
        # Se o termo de busca para o site for vazio, não tenta buscar
        if not search_term:
            print(f"  {site}: Termo de busca vazio. Pulando busca.")
            ean_results[site] = "Termo vazio"
            continue

        prices = find_prices(site, info["url"], info["seletor"], search_term, ean)

        formatted_prices = []
        for p in prices:
            if isinstance(p, float):
                formatted_prices.append(f"R$ {p:.2f}".replace('.', ','))
            else:
                formatted_prices.append(p) 
        
        ean_results[site] = ", ".join(formatted_prices)

        time.sleep(random.uniform(2, 5)) 
    
    all_results.append(ean_results)

# --- Finalização e Salvamento dos Resultados ---
navegador.quit() # Fecha o navegador

results_df = pd.DataFrame(all_results)
output_filename = "precos_produtos_comparacao.xlsx"
results_df.to_excel(output_filename, index=False) # Salva em Excel sem o índice do DataFrame
print(f"\nScraping concluído! Preços salvos em '{output_filename}'")