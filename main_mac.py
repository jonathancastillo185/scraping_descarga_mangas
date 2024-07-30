import os
import requests
import pandas as pd
import ast
import logging
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
import chardet

# Configuración de logging
log_file = "app.log"
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_last_log():
    """Elimina el último archivo de log."""
    if os.path.exists(log_file):
        with open(log_file, 'rb') as file:
            raw_data = file.read()
        encoding = chardet.detect(raw_data)['encoding']
        
        with open(log_file, 'r', encoding=encoding) as file:
            lines = file.readlines()
        
        if lines:
            with open(log_file, 'w', encoding=encoding) as file:
                file.writelines(lines[:-1])  # Escribe el archivo sin la última línea

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

def procesar_dataset(ruta_dataset, anime_name, crear_pdfs=True, eliminar_imagenes=False, descargar_imagenes=True):
    df = pd.read_csv(ruta_dataset)
    
    for index, row in df.iterrows():
        capitulo = row['capitulo']
        paginas = ast.literal_eval(row['paginas'])
        
        ruta_capitulo = os.path.join("mangas", anime_name, f'capitulo_{capitulo}')
        ruta_pdf = os.path.join("mangas", anime_name)
        os.makedirs(ruta_capitulo, exist_ok=True)
        
        lista_imagenes = []

        if descargar_imagenes:
            numero_imagen = 1
            for url in paginas:
                image_path = descargar_imagen(ruta_capitulo, url, numero_imagen)
                if image_path:
                    lista_imagenes.append(image_path)
                numero_imagen += 1
        else:
            # Si no se descargan imágenes, se asume que las imágenes ya están en la carpeta.
            lista_imagenes = [os.path.join(ruta_capitulo, f) for f in os.listdir(ruta_capitulo) if f.endswith('.jpg') or f.endswith('.png')]

        if lista_imagenes and crear_pdfs:
            crear_pdf(ruta_pdf, lista_imagenes, anime_name, capitulo, eliminar_imagenes)


def procesar_url(url, crear_dataset=True, crear_pdfs=True, eliminar_imagenes=False, combinar_capitulos=True, var_descargar_imagenes = True):
    anime_name = extract_anime_name(url)
    base_path = os.path.join(os.getcwd(), "mangas", anime_name, "dataset")
    base_path_pdf_completo = os.path.join(os.getcwd(), "mangas", anime_name)
    csv_path = os.path.join(base_path, "capitulos_completos.csv")

    # Crear las rutas si no existen
    os.makedirs(base_path, exist_ok=True)
    os.makedirs(base_path_pdf_completo, exist_ok=True)
    
    if crear_dataset:
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

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
        df.to_csv(csv_path, index=False)
        logging.info(f'Dataset guardado en: {csv_path}')

    if crear_pdfs:
        procesar_dataset(csv_path, anime_name, crear_pdfs, eliminar_imagenes, descargar_imagenes = var_descargar_imagenes)
    
    if combinar_capitulos:
        ruta_pdfs_combinados = mover_pdfs_a_carpeta(base_path_pdf_completo)
        combinar_pdfs(ruta_pdfs_combinados, anime_name)

    if crear_pdfs:
        procesar_dataset(csv_path, anime_name, crear_pdfs, eliminar_imagenes, var_descargar_imagenes)
        mover_pdfs_a_carpeta(base_path_pdf_completo)

    if combinar_capitulos:
        ruta_pdfs_combinados = mover_pdfs_a_carpeta(base_path_pdf_completo)
        combinar_pdfs(ruta_pdfs_combinados, anime_name, combinar_capitulos)

# Interfaz gráfica con Tkinter
def ejecutar_proceso():
    clean_last_log()
    var_url = entry_url.get()
    var_crear_dataset = crear_dataset_var.get()
    var_crear_pdfs = crear_pdfs_var.get()
    var_eliminar_imagenes = eliminar_imagenes_var.get()
    var_combinar_capitulos = combinar_capitulos_var.get()
    var_descargar_imagenes = descargar_imagenes_var.get()
    
    procesar_url(var_url, var_crear_dataset, var_crear_pdfs, var_eliminar_imagenes, var_combinar_capitulos, var_descargar_imagenes)

    with open(log_file, 'r') as file:
        logs = file.read()
        log_text.config(state=tk.NORMAL)
        log_text.delete(1.0, tk.END)
        log_text.insert(tk.END, logs)
        log_text.config(state=tk.DISABLED)

root = tk.Tk()
root.title("Manga Downloader")

frame = tk.Frame(root)
frame.pack(pady=20)

label_url = tk.Label(frame, text="URL del manga:")
label_url.grid(row=0, column=0, sticky="e")
entry_url = tk.Entry(frame, width=50)
entry_url.grid(row=0, column=1)

crear_dataset_var = tk.BooleanVar(value=True)
crear_dataset_check = tk.Checkbutton(frame, text="Crear dataset", variable=crear_dataset_var)
crear_dataset_check.grid(row=1, columnspan=2, sticky="w")

crear_pdfs_var = tk.BooleanVar(value=True)
crear_pdfs_check = tk.Checkbutton(frame, text="Crear PDFs", variable=crear_pdfs_var)
crear_pdfs_check.grid(row=2, columnspan=2, sticky="w")

eliminar_imagenes_var = tk.BooleanVar(value=False)
eliminar_imagenes_check = tk.Checkbutton(frame, text="Eliminar imágenes después de crear PDFs", variable=eliminar_imagenes_var)
eliminar_imagenes_check.grid(row=3, columnspan=2, sticky="w")

combinar_capitulos_var = tk.BooleanVar(value=True)
combinar_capitulos_check = tk.Checkbutton(frame, text="Combinar capítulos en un solo PDF", variable=combinar_capitulos_var)
combinar_capitulos_check.grid(row=4, columnspan=2, sticky="w")

descargar_imagenes_var = tk.BooleanVar(value=True)
descargar_imagenes_check = tk.Checkbutton(frame, text="Descargar imágenes", variable=descargar_imagenes_var)
descargar_imagenes_check.grid(row=5, columnspan=2, sticky="w")

btn_ejecutar = tk.Button(frame, text="Ejecutar", command=ejecutar_proceso)
btn_ejecutar.grid(row=6, columnspan=2, pady=10)

log_text = scrolledtext.ScrolledText(root, width=80, height=20, state=tk.DISABLED)
log_text.pack(pady=10)

root.mainloop()
