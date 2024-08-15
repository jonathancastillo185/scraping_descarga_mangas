import os
import requests
import pandas as pd
import ast
import logging
from concurrent.futures import ThreadPoolExecutor
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

# Configuración de logging
log_file = "app.log"
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_last_log():
    """Elimina el último archivo de log."""
    if os.path.exists(log_file):
        with open(log_file, 'r') as file:
            lines = file.readlines()
        
        if lines:
            with open(log_file, 'w') as file:
                file.writelines(lines[:-1])  # Escribe el archivo sin la última línea

def file_exists(filepath):
    """Verifica si un archivo existe."""
    return os.path.exists(filepath)

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
    try:
        response = requests.get(url_imagen)
        response.raise_for_status()
        if 'image' in response.headers.get('content-type', ''):
            os.makedirs(ruta_guardado, exist_ok=True)
            image_name = f'{numero_imagen}.jpg'
            image_path = os.path.join(ruta_guardado, image_name)
            with open(image_path, 'wb') as f:
                f.write(response.content)
            return image_path
        else:
            logging.warning(f'Error al descargar la imagen. Tipo de contenido: {response.headers.get("content-type")}')
            return None
    except requests.RequestException as e:
        logging.error(f'Error al descargar la imagen: {e}')
        return None

def descargar_imagen_async(url_imagen, ruta_guardado, numero_imagen):
    return descargar_imagen(ruta_guardado, url_imagen, numero_imagen)

def es_imagen_valida(image_path):
    try:
        with Image.open(image_path) as img:
            img.verify()
        return True
    except (IOError, SyntaxError) as e:
        logging.error(f'Archivo de imagen inválido o corrupto: {image_path}. Error: {e}')
        return False

def convertir_a_jpeg(image_path):
    try:
        with Image.open(image_path) as img:
            if img.format != 'JPEG':
                rgb_im = img.convert('RGB')
                rgb_im.save(image_path, 'JPEG', quality=100)
                logging.info(f'Imagen convertida a JPEG: {image_path}')
    except Exception as e:
        logging.error(f'Error al convertir la imagen: {image_path}. Error: {e}')

def crear_pdf(ruta_guardado, lista_imagenes, anime_name, capitulo, eliminar_imagenes=False):
    pdf = FPDF()
    for image_path in lista_imagenes:
        if es_imagen_valida(image_path):
            convertir_a_jpeg(image_path)
            pdf.add_page()
            pdf.image(image_path, 0, 0, 210, 297)  # Ajusta el tamaño según sea necesario pdf.image(image_path, 0, 0, 210, 297)
        else:
            logging.warning(f'Imagen omitida debido a errores: {image_path}')
            os.remove(image_path)
    if capitulo < 10:
        capitulo = f"0{capitulo}"
    pdf_name = f"{anime_name}_capitulo_{capitulo}.pdf".replace(" ", "_")
    pdf_path = os.path.join(ruta_guardado, pdf_name)
    pdf.output(pdf_path)
    logging.info(f'PDF guardado en: {pdf_path}')
    
    # Eliminar las imágenes después de crear el PDF
    if eliminar_imagenes:
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

def guardar_url_manga(url, anime_name):
    """Guarda la URL del manga en un archivo de texto dentro de la carpeta del manga."""
    base_path = os.path.join(os.getcwd(), "mangas", anime_name)
    os.makedirs(base_path, exist_ok=True)
    
    url_file_path = os.path.join(base_path, "url.txt")
    with open(url_file_path, 'w') as file:
        file.write(url)
    logging.info(f'URL guardada en: {url_file_path}')


def guardar_url(ruta_carpeta, url):
    """Guarda el URL del manga en un archivo de texto dentro de su carpeta."""
    url_file = os.path.join(ruta_carpeta, "url.txt")
    with open(url_file, "w") as f:
        f.write(url)
    logging.info(f'URL guardado en: {url_file}')



def combinar_pdfs(ruta_pdfs_combinados, anime_name, start=None, end=None, interval=None):
    pdfs = buscar_pdfs_en_directorios(ruta_pdfs_combinados)
    pdfs.sort()  # Ordenar por nombre, asumiendo que los nombres incluyen números de capítulo

    if not pdfs:
        logging.warning("No se encontraron archivos PDF para combinar.")
        return

    # Extraer los números de capítulo de los nombres de los archivos PDF
    pdf_chapters = []
    for pdf in pdfs:
        try:
            # Asumiendo que los archivos PDF tienen el formato `Nombre_Manga_capitulo_XX.0.pdf`
            chapter_num = float(pdf.split('_capitulo_')[1].split('.pdf')[0])
            pdf_chapters.append((chapter_num, pdf))
        except (IndexError, ValueError) as e:
            logging.warning(f"El archivo {pdf} no sigue el formato esperado y será omitido. Error: {e}")
            continue
    
    # Ordenar por número de capítulo
    pdf_chapters.sort()

    # Si `start` o `end` son None, ajustarlos para cubrir el rango completo
    start = start if start is not None else 0
    end = end if end is not None else len(pdf_chapters)

    # Filtrar PDFs según el rango seleccionado
    selected_pdfs = [pdf for num, pdf in pdf_chapters if start <= num <= end]

    if interval is None or interval <= 0:
        interval = len(selected_pdfs)  # Combina todos en uno si no se especifica intervalo válido

    logging.info(f'Combinando PDFs desde capítulo {start} hasta {end} con un intervalo de {interval}.')

    for i in range(0, len(selected_pdfs), interval):
        writer = PdfWriter()
        chunk = selected_pdfs[i:i+interval]

        logging.info(f'Combining PDFs: {chunk}')

        for pdf_path in chunk:
            with open(pdf_path, 'rb') as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    writer.add_page(page)

        # Ajustar los nombres de los archivos combinados para reflejar correctamente el rango de capítulos
        pdf_combined_name = f"{anime_name}_capitulos_{chunk[0].split('_capitulo_')[1].split('.pdf')[0].replace('.', '_')}_a_{chunk[-1].split('_capitulo_')[1].split('.pdf')[0].replace('.', '_')}.pdf".replace(" ", "_")
        pdf_combined_path = os.path.join(ruta_pdfs_combinados, pdf_combined_name)
        with open(pdf_combined_path, 'wb') as f:
            writer.write(f)

        logging.info(f'PDF combinado guardado en: {pdf_combined_path}')

def leer_url(ruta_carpeta):
    """Lee el URL del manga desde el archivo de texto dentro de su carpeta."""
    url_file = os.path.join(ruta_carpeta, "url.txt")
    if os.path.exists(url_file):
        with open(url_file, "r") as f:
            url = f.read().strip()
        return url
    else:
        logging.warning(f'No se encontró el archivo con el URL en: {url_file}')
        return None


def mover_pdfs_a_carpeta(ruta_base):
    ruta_pdfs = os.path.join(ruta_base)
    ruta_pdfs_combinados = os.path.join(ruta_base, 'pdfs_combinados')
    os.makedirs(ruta_pdfs_combinados, exist_ok=True)

    pdfs = [f for f in os.listdir(ruta_pdfs) if f.endswith('.pdf')]
    logging.info(f'PDFs encontrados para mover: {pdfs}')

    for pdf in pdfs:
        pdf_path = os.path.join(ruta_pdfs, pdf)
        logging.info(f'Moviendo PDF: {pdf_path} a {ruta_pdfs_combinados}')
        shutil.move(pdf_path, os.path.join(ruta_pdfs_combinados, pdf))

    return ruta_pdfs_combinados

def crear_dataset(url, csv_path, overwrite=False):
    """Crea el dataset CSV desde la URL del manga."""
    if file_exists(csv_path) and not overwrite:
        logging.info(f'Dataset ya existe: {csv_path}')
        return
    else:
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

        try:
            driver.get(url)

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
                            logging.error(f"Error al procesar el elemento {idx}: {e}")

                    capitulos_complt["capitulo"].append(x)
                    capitulos_complt["paginas"].append(url_paginas)

                except Exception as e:
                    logging.error(f"Error al procesar la página {x}/{i}: {e}")

            df = pd.DataFrame(capitulos_complt)
            df.to_csv(csv_path, index=False)
            logging.info(f'Dataset guardado en: {csv_path}')

        finally:
            driver.quit()

def procesar_dataset(ruta_dataset, anime_name, crear_pdfs=True, eliminar_imagenes=False, descargar_imagenes=True, overwrite=False):
    if not file_exists(ruta_dataset):
        logging.error(f'No se encontró el dataset: {ruta_dataset}')
        return

    df = pd.read_csv(ruta_dataset)
    
    for index, row in df.iterrows():
        capitulo = row['capitulo']
        paginas = ast.literal_eval(row['paginas'])
        
        ruta_capitulo = os.path.join("mangas", anime_name, f'capitulo_{capitulo}')
        ruta_pdf = os.path.join("mangas", anime_name)
        pdf_name = f"{anime_name}_capitulo_{capitulo}.pdf".replace(" ", "_")
        pdf_path = os.path.join(ruta_pdf, pdf_name)

        if file_exists(pdf_path) and not overwrite:
            logging.info(f'PDF ya existe: {pdf_path}')
            continue

        os.makedirs(ruta_capitulo, exist_ok=True)
        lista_imagenes = []

        if descargar_imagenes:
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(descargar_imagen_async, url, ruta_capitulo, idx) for idx, url in enumerate(paginas)]
                for future in futures:
                    image_path = future.result()
                    if image_path:
                        lista_imagenes.append(image_path)
        else:
            # Si no se descargan imágenes, se asume que las imágenes ya están en la carpeta.
            lista_imagenes = [os.path.join(ruta_capitulo, f) for f in os.listdir(ruta_capitulo) if f.endswith('.jpg') or f.endswith('.png')]

        if lista_imagenes and crear_pdfs:
            crear_pdf(ruta_pdf, lista_imagenes, anime_name, capitulo, eliminar_imagenes)

def procesar_url(url, crear_dataset_var=True, crear_pdfs_var=True, eliminar_imagenes_var=False, combinar_capitulos_var=True, descargar_imagenes_var=True, overwrite=False):
    anime_name = extract_anime_name(url)
    base_path = os.path.join(os.getcwd(), "mangas", anime_name, "dataset")
    base_path_pdf_completo = os.path.join(os.getcwd(), "mangas", anime_name)
    csv_path = os.path.join(base_path, "capitulos_completos.csv")

    # Crear las rutas si no existen
    os.makedirs(base_path, exist_ok=True)
    os.makedirs(base_path_pdf_completo, exist_ok=True)
    
    # Guardar el URL del manga
    guardar_url(base_path_pdf_completo, url)
    
    if crear_dataset_var:
        crear_dataset(url, csv_path, overwrite)

    if crear_pdfs_var:
        procesar_dataset(csv_path, anime_name, crear_pdfs_var, eliminar_imagenes_var, descargar_imagenes_var, overwrite)
    
    if combinar_capitulos_var:
        ruta_pdfs_combinados = mover_pdfs_a_carpeta(base_path_pdf_completo)
        combinar_pdfs(ruta_pdfs_combinados, anime_name)



def run_processes(urls, crear_dataset_var, crear_pdfs_var, eliminar_imagenes_var, combinar_capitulos_var, overwrite_var):
    clean_last_log()
    
    for url in urls:
        procesar_url(url, crear_dataset_var=crear_dataset_var, crear_pdfs_var=crear_pdfs_var, eliminar_imagenes_var=eliminar_imagenes_var, combinar_capitulos_var=combinar_capitulos_var, descargar_imagenes_var=True, overwrite=overwrite_var)
    
    logging.info("Todos los animes han sido exportados correctamente.")

def obtener_mangas_descargados():
    base_dir = os.path.join(os.getcwd(), "mangas")
    mangas = []
    if os.path.exists(base_dir):
        for manga in os.listdir(base_dir):
            ruta_manga = os.path.join(base_dir, manga)
            if os.path.isdir(ruta_manga):
                mangas.append(manga)
    return mangas

def obtener_info_manga(manga_name):
    base_dir = os.path.join(os.getcwd(), "mangas", manga_name)
    dataset_path = os.path.join(base_dir, "dataset", "capitulos_completos.csv")
    imagenes_existentes = []
    pdfs_existentes = []
    combinados_existentes = []

    if os.path.exists(dataset_path):
        df = pd.read_csv(dataset_path)
        imagenes_existentes = df['capitulo'].tolist()

    pdfs = buscar_pdfs_en_directorios(base_dir)
    for pdf in pdfs:
        if "todos_los_capitulos" in pdf:
            combinados_existentes.append(pdf)
        else:
            pdfs_existentes.append(pdf)

    return {
        "dataset": file_exists(dataset_path),
        "imagenes": imagenes_existentes,
        "pdfs": pdfs_existentes,
        "combinados": combinados_existentes
    }
