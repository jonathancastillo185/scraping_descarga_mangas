import os
import requests
import pandas as pd
import ast
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Función para extraer el nombre del anime desde la URL
def extract_anime_name(url):
    parts = url.split('/manga/')
    if len(parts) > 1:
        name = parts[1].split('/')[0]
        return name.replace('-', ' ').title()
    return None

def extract_segmento_url(url, x, i):
    parts = url.split('/')
    if len(parts) > 1:
        return '/'.join(parts[:6]) + '/' + x + '/' + i
    return None

def descargar_imagen(ruta_guardado, url_imagen, numero_imagen):
    response = requests.get(url_imagen)
    if response.status_code == 200:
        os.makedirs(ruta_guardado, exist_ok=True)
        image_name = f'{numero_imagen}.jpg'
        image_path = os.path.join(ruta_guardado, image_name)
        with open(image_path, 'wb') as f:
            f.write(response.content)
        print(f'Imagen guardada en: {image_path}')
    else:
        print(f'Error al descargar la imagen. Código de estado: {response.status_code}')

def procesar_dataset(ruta_dataset):
    df = pd.read_csv(ruta_dataset)
    for index, row in df.iterrows():
        anime_name_clean = row['anime']
        capitulo = row['capitulo']
        paginas = ast.literal_eval(row['paginas'])
        
        ruta_capitulo = os.path.join("mangas", anime_name_clean, f'capitulo_{capitulo}')
        os.makedirs(ruta_capitulo, exist_ok=True)
        
        numero_imagen = 1
        for url in paginas:
            descargar_imagen(ruta_capitulo, url, numero_imagen)
            numero_imagen += 1

def main():
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    url = print(input("Ingrese la url del manga: "))


    anime_name = extract_anime_name(url)
    anime_name_clean = "".join(char for char in anime_name if char.isalnum() or char.isspace()).replace(" ", "_")

    driver.get(url)

    try:
        select_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="ChapList"]'))
        )

        options = select_element.find_elements(By.TAG_NAME, 'option')

        cod = []
        capitulo = []

        for option in options:
            cod.append(option.get_attribute('value'))
            capitulo.append(option.text)

        capitulos_complt = {"capitulo": [], "paginas": []}

        for x, i in zip(capitulo, cod):
            driver.get(extract_segmento_url(url, x, i))

            try:
                select_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="PageList"]'))
                )

                options = select_element.find_elements(By.TAG_NAME, 'option')

                pagina = [opt.text for opt in options]

                boton_next = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '/html/body/div/section/div/div/div[2]/div[1]/div/div/div[5]/div/button[2]'))
                )

                for _ in range(len(pagina) - 1):
                    boton_next.click()

                url_paginas = []

                for idx in range(1, len(pagina) + 1):
                    try:
                        src_pag = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, f'/html/body/div/section/div/div/div[2]/div[2]/div[1]/a[{idx}]'))
                        )

                        img_element = src_pag.find_element(By.TAG_NAME, 'img')
                        src = img_element.get_attribute('src')

                        url_paginas.append(src)
                    except Exception as e:
                        print(f"Error al procesar el elemento {idx}: {e}")

                capitulos_complt["capitulo"].append(x)
                capitulos_complt["paginas"].append(url_paginas)

            except Exception as e:
                print(f"Error al procesar la página {x}/{i}: {e}")

    finally:
        driver.quit()

    df = pd.DataFrame(capitulos_complt)
    df.insert(0, 'anime', anime_name)

    base_path = os.path.join(os.getcwd(), "mangas", anime_name, "dataset")
    os.makedirs(base_path, exist_ok=True)

    csv_path = os.path.join(base_path, "capitulos_completos.csv")
    df.to_csv(csv_path, index=False)
    print(f"Archivo CSV guardado en: {csv_path}")

    procesar_dataset(csv_path)

if __name__ == "__main__":
    main()
