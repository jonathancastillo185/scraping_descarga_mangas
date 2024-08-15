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
import tkinter as tk
from tkinter import scrolledtext

# Configuración de logging
log_file = "app.log"
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

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

def combinar_pdfs(ruta_pdfs_combinados, anime_name, combinar_capitulos=True):
    if combinar_capitulos:
        pdfs = buscar_pdfs_en_directorios(ruta_pdfs_combinados)
        pdfs.sort()  # Ordenar por nombre, asumiendo que los nombres incluyen números de capítulo

        if not pdfs:
            logging.warning("No se encontraron archivos PDF para combinar.")
            return

        writer = PdfWriter()

        # Añadir los PDFs de capítulos
        for pdf_path in pdfs:
            logging.info(f'Leyendo PDF: {pdf_path}')
            with open(pdf_path, 'rb') as f:
                reader = PdfReader(f)

                for page in reader.pages:
                    writer.add_page(page)

        pdf_combined_name = f"{anime_name}_todos_los_capitulos.pdf".replace(" ", "_")
        pdf_combined_path = os.path.join(ruta_pdfs_combinados, pdf_combined_name)
        with open(pdf_combined_path, 'wb') as f:
            writer.write(f)

        logging.info(f'PDF combinado guardado en: {pdf_combined_path}')

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

def crear_dataset(driver, url, csv_path, overwrite=False):
    """Crea el dataset CSV desde la URL del manga."""
    if file_exists(csv_path) and not overwrite:
        logging.info(f'Dataset ya existe: {csv_path}')
        return
    else:
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
                            logging.error(f"Error al procesar el elemento {idx}: {e}")

                    capitulos_complt["capitulo"].append(x)
                    capitulos_complt["paginas"].append(url_paginas)

                except Exception as e:
                    logging.error(f"Error al procesar la página {x}/{i}: {e}")

        finally:
            df = pd.DataFrame(capitulos_complt)
            df.to_csv(csv_path, index=False)
            logging.info(f'Dataset guardado en: {csv_path}')

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

def procesar_url(url, driver, crear_dataset_var=True, crear_pdfs_var=True, eliminar_imagenes_var=False, combinar_capitulos_var=True, descargar_imagenes_var=True, overwrite=False):
    anime_name = extract_anime_name(url)
    base_path = os.path.join(os.getcwd(), "mangas", anime_name, "dataset")
    base_path_pdf_completo = os.path.join(os.getcwd(), "mangas", anime_name)
    csv_path = os.path.join(base_path, "capitulos_completos.csv")

    # Crear las rutas si no existen
    os.makedirs(base_path, exist_ok=True)
    os.makedirs(base_path_pdf_completo, exist_ok=True)
    
    if crear_dataset_var:
        crear_dataset(driver, url, csv_path, overwrite)

    if crear_pdfs_var:
        procesar_dataset(csv_path, anime_name, crear_pdfs_var, eliminar_imagenes_var, descargar_imagenes_var, overwrite)
    
    if combinar_capitulos_var:
        ruta_pdfs_combinados = mover_pdfs_a_carpeta(base_path_pdf_completo)
        combinar_pdfs(ruta_pdfs_combinados, anime_name)

def run_processes(urls, crear_dataset_var, crear_pdfs_var, eliminar_imagenes_var, combinar_capitulos_var, overwrite_var):
    clean_last_log()
    
    # Reutilización del WebDriver
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        for url in urls:
            procesar_url(url, driver, crear_dataset_var=crear_dataset_var, crear_pdfs_var=crear_pdfs_var, eliminar_imagenes_var=eliminar_imagenes_var, combinar_capitulos_var=combinar_capitulos_var, descargar_imagenes_var=True, overwrite=overwrite_var)
        logging.info("Todos los animes han sido exportados correctamente.")
    finally:
        driver.quit()

def start_gui():
    root = tk.Tk()
    root.title("Manga Downloader")

    def on_start_button_click():
        urls = url_text.get("1.0", tk.END).strip().split('\n')
        crear_dataset_var = var_crear_dataset.get()
        crear_pdfs_var = var_crear_pdfs.get()
        eliminar_imagenes_var = var_eliminar_imagenes.get()
        combinar_capitulos_var = var_combinar_capitulos.get()
        overwrite_var = var_overwrite.get()
        
        # Limpiar logs antes de empezar el proceso
        clean_last_log()
        
        # Ejecutar procesos en un hilo separado para no bloquear la interfaz
        import threading
        threading.Thread(target=run_processes, args=(urls, crear_dataset_var, crear_pdfs_var, eliminar_imagenes_var, combinar_capitulos_var, overwrite_var)).start()

    tk.Label(root, text="URLs del Anime (una por línea):").pack(pady=5)
    url_text = scrolledtext.ScrolledText(root, width=60, height=15)
    url_text.pack(pady=5)

    var_crear_dataset = tk.BooleanVar(value=True)
    var_crear_pdfs = tk.BooleanVar(value=True)
    var_eliminar_imagenes = tk.BooleanVar(value=False)
    var_combinar_capitulos = tk.BooleanVar(value=True)
    var_overwrite = tk.BooleanVar(value=False)

    tk.Checkbutton(root, text="Crear Dataset", variable=var_crear_dataset).pack(pady=5)
    tk.Checkbutton(root, text="Crear PDFs", variable=var_crear_pdfs).pack(pady=5)
    tk.Checkbutton(root, text="Eliminar Imágenes", variable=var_eliminar_imagenes).pack(pady=5)
    tk.Checkbutton(root, text="Combinar Capítulos", variable=var_combinar_capitulos).pack(pady=5)
    tk.Checkbutton(root, text="Sobrescribir Archivos Existentes", variable=var_overwrite).pack(pady=5)

    start_button = tk.Button(root, text="Iniciar", command=on_start_button_click)
    start_button.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    start_gui()
