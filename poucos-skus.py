from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Configurar o navegador
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
navegador = webdriver.Chrome(options=options)

# EAN e termo de busca alternativo para Mercado Livre
ean = "7503002941409"
termo_busca_ml = "Dove Shampoo 400ml"  # Ajuste conforme o produto
resultados = {}

# Função para buscar preços
def buscar_precos(site, url_base, seletor_preco, termo):
    navegador.get(url_base.format(termo))
    try:
        # Aguarda até que os preços estejam visíveis (máximo 10 segundos)
        WebDriverWait(navegador, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, seletor_preco))
        )
        precos = []
        if site == "Mercado Livre":
            itens = navegador.find_elements(By.CSS_SELECTOR, "li.ui-search-layout__item")
            for item in itens[:5]:
                try:
                    texto_item = item.text.lower()
                    if str(ean) in texto_item or "dove shampoo" in texto_item.lower():  # Filtro mais flexível
                        # Captura preço completo (inteiro + centavos)
                        preco_elem = item.find_element(By.CSS_SELECTOR, seletor_preco)
                        preco = preco_elem.text
                        # Busca centavos, se disponíveis
                        cents_elem = item.find_elements(By.CSS_SELECTOR, "span.andes-money-amount__cents")
                        if cents_elem:
                            preco += "," + cents_elem[0].text
                        precos.append(preco)
                except:
                    continue
        elif site == "Amazon":
            itens = navegador.find_elements(By.CSS_SELECTOR, "div.s-result-item")
            for item in itens[:5]:
                try:
                    # Captura parte inteira, fracionária e símbolo
                    whole = item.find_element(By.CSS_SELECTOR, "span.a-price-whole").text
                    fraction = item.find_element(By.CSS_SELECTOR, "span.a-price-fraction").text
                    symbol = item.find_element(By.CSS_SELECTOR, "span.a-price-symbol").text
                    preco = f"{symbol} {whole},{fraction}"
                    # Prioriza vendedor Amazon.com.br, se disponível
                    seller = item.find_elements(By.CSS_SELECTOR, "span.a-size-small")
                    if any("Amazon.com.br" in s.text for s in seller) or not seller:
                        precos.append(preco)
                except:
                    continue
        else:  # Magazine Luiza
            precos = [elem.text for elem in navegador.find_elements(By.CSS_SELECTOR, seletor_preco)[:5]]
        print(f"{site}: Encontrados {len(precos)} resultados")
        return precos if precos else ["Nenhum preço encontrado"]
    except Exception as e:
        print(f"{site}: Erro ao buscar preços - {str(e)}")
        return ["Erro ao buscar preços"]

# Sites e seletores
sites = {
    "Mercado Livre": {
        "url": "https://www.mercadolivre.com.br/search?query={}",
        "seletor": "span.andes-money-amount__fraction",
        "termo": termo_busca_ml
    },
    "Amazon": {
        "url": "https://www.amazon.com.br/s?k={}",
        "seletor": "span.a-price",
        "termo": ean
    },
    "Magazine Luiza": {
        "url": "https://www.magazineluiza.com.br/busca/{}",
        "seletor": "span.sc-kpDqfm.eCPtRw",
        "termo": ean
    }
}

# Buscar preços
for site, info in sites.items():
    resultados[site] = buscar_precos(site, info["url"], info["seletor"], info["termo"])
    time.sleep(2)  # Pausa para evitar bloqueios

# Fechar o navegador
navegador.quit()

# Salvar resultados
with open("C:/precos/precos_ean_multi.txt", "w", encoding="utf-8") as arquivo:
    arquivo.write(f"Preços para EAN '{ean}':\n\n")
    for site, precos in resultados.items():
        arquivo.write(f"{site}:\n")
        for i, preco in enumerate(precos, 1):
            arquivo.write(f"  Item {i}: {preco}\n")
        arquivo.write("\n")

print(f"Preços salvos em 'C:/precos/precos_ean_multi.txt' para EAN '{ean}'")