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
from fpdf import FPDF
from PIL import Image
from PyPDF2 import PdfWriter, PdfReader
import shutil

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
    if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
        os.makedirs(ruta_guardado, exist_ok=True)
        image_name = f'{numero_imagen}.jpg'
        image_path = os.path.join(ruta_guardado, image_name)
        with open(image_path, 'wb') as f:
            f.write(response.content)
        return image_path
    else:
        print(f'Error al descargar la imagen. Código de estado: {response.status_code}, Tipo de contenido: {response.headers.get("content-type")}')
        return None

def es_imagen_valida(image_path):
    try:
        with Image.open(image_path) as img:
            img.verify()
        return True
    except (IOError, SyntaxError) as e:
        print(f'Archivo de imagen inválido o corrupto: {image_path}. Error: {e}')
        return False

def convertir_a_jpeg(image_path):
    try:
        with Image.open(image_path) as img:
            if img.format != 'JPEG':
                rgb_im = img.convert('RGB')
                rgb_im.save(image_path, 'JPEG', quality=100)
                print(f'Imagen convertida a JPEG: {image_path}')
    except Exception as e:
        print(f'Error al convertir la imagen: {image_path}. Error: {e}')

def crear_pdf(ruta_guardado, lista_imagenes, anime_name, capitulo):
    pdf = FPDF()
    for image_path in lista_imagenes:
        if es_imagen_valida(image_path):
            convertir_a_jpeg(image_path)
            pdf.add_page()
            pdf.image(image_path, 0, 0, 210, 297)  # Ajusta el tamaño según sea necesario
        else:
            print(f'Imagen omitida debido a errores: {image_path}')
            os.remove(image_path)
    pdf_name = f"{anime_name}_capitulo_{capitulo}.pdf".replace(" ", "_")
    pdf_path = os.path.join(ruta_guardado, pdf_name)
    pdf.output(pdf_path)
    print(f'PDF guardado en: {pdf_path}')
    
    # Eliminar las imágenes después de crear el PDF
    for image_path in lista_imagenes:
        if os.path.exists(image_path):
            os.remove(image_path)

def buscar_pdfs_en_directorios(base_path):
    """Busca todos los archivos PDF en todos los subdirectorios dentro de base_path."""
    pdf_paths = []
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.endswith('.pdf'):
                pdf_paths.append(os.path.join(root, file))
    return pdf_paths

def combinar_pdfs(ruta_pdfs_combinados, anime_name):
    pdfs = buscar_pdfs_en_directorios(ruta_pdfs_combinados)
    pdfs.sort()  # Ordenar por nombre, asumiendo que los nombres incluyen números de capítulo

    if not pdfs:
        print("No se encontraron archivos PDF para combinar.")
        return

    writer = PdfWriter()

    # Añadir los PDFs de capítulos
    for pdf_path in pdfs:
        print(f'Leyendo PDF: {pdf_path}')  # Debug: Mostrar cada PDF que se está leyendo
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)

            for page in reader.pages:
                writer.add_page(page)

    pdf_combined_name = f"{anime_name}_todos_los_capitulos.pdf".replace(" ", "_")
    pdf_combined_path = os.path.join(ruta_pdfs_combinados, pdf_combined_name)
    with open(pdf_combined_path, 'wb') as f:
        writer.write(f)

    print(f'PDF combinado guardado en: {pdf_combined_path}')

def mover_pdfs_a_carpeta(ruta_base):
    ruta_pdfs = os.path.join(ruta_base)
    ruta_pdfs_combinados = os.path.join(ruta_base, 'pdfs_combinados')
    os.makedirs(ruta_pdfs_combinados, exist_ok=True)

    pdfs = [f for f in os.listdir(ruta_pdfs) if f.endswith('.pdf')]
    print(f'PDFs encontrados para mover: {pdfs}')  # Debug: Mostrar los PDFs encontrados

    for pdf in pdfs:
        pdf_path = os.path.join(ruta_pdfs, pdf)
        print(f'Moviendo PDF: {pdf_path} a {ruta_pdfs_combinados}')  # Debug: Mostrar ruta de movimiento
        shutil.move(pdf_path, os.path.join(ruta_pdfs_combinados, pdf))

    return ruta_pdfs_combinados

def procesar_dataset(ruta_dataset, anime_name):
    df = pd.read_csv(ruta_dataset)
    for index, row in df.iterrows():
        capitulo = row['capitulo']
        paginas = ast.literal_eval(row['paginas'])
        
        ruta_capitulo = os.path.join("mangas", anime_name, f'capitulo_{capitulo}')
        ruta_pdf = os.path.join("mangas", anime_name)
        os.makedirs(ruta_capitulo, exist_ok=True)
        
        numero_imagen = 1
        lista_imagenes = []
        for url in paginas:
            image_path = descargar_imagen(ruta_capitulo, url, numero_imagen)
            if image_path:
                lista_imagenes.append(image_path)
            numero_imagen += 1
        
        if lista_imagenes:
            crear_pdf(ruta_pdf, lista_imagenes, anime_name, capitulo)

def procesar_url(url):
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    anime_name = extract_anime_name(url)

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
    base_path_pdf_completo = os.path.join(os.getcwd(), "mangas", anime_name)
    os.makedirs(base_path, exist_ok=True)

    csv_path = os.path.join(base_path, "capitulos_completos.csv")
    df.to_csv(csv_path, index=False)
    print(f"Archivo CSV guardado en: {csv_path}")

    procesar_dataset(csv_path, anime_name)

    # Mover los PDFs generados y combinarlos
    ruta_pdfs_combinados = mover_pdfs_a_carpeta(base_path)
    combinar_pdfs(base_path_pdf_completo, anime_name)

def main():
    urls = [
        'https://inmanga.com/ver/manga/Torre-de-Dios/03/0dad8676-e303-4f84-9697-6e915dc780cf',
        'https://inmanga.com/ver/manga/Boku-no-Hero-Academia/01/51268107-c3b3-4138-b991-8e8afb42f776',
        'https://inmanga.com/ver/manga/Jujutsu-Kaisen/1/8348a510-b313-4916-8787-80278967e2e1',
        'https://inmanga.com/ver/manga/Dr-Stone/1/2bd229a3-ec30-49ef-abb0-6fbef6ccbcb1',
        'https://inmanga.com/ver/manga/Tales-of-Demons-and-Gods/02/21608123-31fd-4645-8b43-3b61a4e21e87',
        'https://inmanga.com/ver/manga/Goblin-Slayer/1/a3ee5be2-18e2-4dac-8195-d6382e69487b',
        'https://inmanga.com/ver/manga/Goblin-Slayer-Brand-New-Day/1/bf621017-201a-4bca-9601-cd4786adf3de',
        'https://inmanga.com/ver/manga/Goblin-Slayer-Year-One/1/7d2722f2-ed53-4198-9d48-b98660ae860d',
        'https://inmanga.com/ver/manga/Goblin-Slayer/1/a3ee5be2-18e2-4dac-8195-d6382e69487b',
        'https://inmanga.com/ver/manga/Goblin-Slayer-Tsubanari-no-Daikatana/1/0471c6d4-70f7-46de-a038-e4c82283411c',
        'https://inmanga.com/ver/manga/70-Oku-no-Hari/1/1c169c3f-0299-442a-b90d-8259110f4f7e'
    ]
    
    for url in urls:
        procesar_url(url)

if __name__ == "__main__":
    main()
