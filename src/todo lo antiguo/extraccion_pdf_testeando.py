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
import tkinter as tk
from tkinter import scrolledtext, messagebox, Checkbutton, BooleanVar, Entry, Label

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
            pdf.image(image_path, 0, 0, 210, 297)
        else:
            print(f'Imagen omitida debido a errores: {image_path}')
            os.remove(image_path)
    pdf_name = f"{anime_name}_capitulo_{capitulo}.pdf".replace(" ", "_")
    pdf_path = os.path.join(ruta_guardado, pdf_name)
    pdf.output(pdf_path)
    print(f'PDF guardado en: {pdf_path}')
    
    for image_path in lista_imagenes:
        if os.path.exists(image_path):
            os.remove(image_path)

def buscar_pdfs_en_directorios(base_path):
    pdf_paths = []
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.endswith('.pdf'):
                pdf_paths.append(os.path.join(root, file))
    return pdf_paths

def extraer_numero_capitulo(pdf_name):
    import re
    match = re.search(r'capitulo_(\d+(?:\.\d+)?)', pdf_name)
    if match:
        return float(match.group(1))
    return None

def combinar_pdfs(ruta_pdfs_combinados, anime_name, combinar=True):
    if not combinar:
        return

    pdfs = buscar_pdfs_en_directorios(ruta_pdfs_combinados)
    pdfs.sort(key=lambda x: extraer_numero_capitulo(os.path.basename(x)))

    if not pdfs:
        print("No se encontraron archivos PDF para combinar.")
        return

    writer = PdfWriter()

    for pdf_path in pdfs:
        print(f'Leyendo PDF: {pdf_path}')
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            for page in reader.pages:
                writer.add_page(page)

    pdf_combined_name = f"{anime_name}_todos_los_capitulos.pdf".replace(" ", "_")
    pdf_combined_path = os.path.join(ruta_pdfs_combinados, pdf_combined_name)
    with open(pdf_combined_path, 'wb') as f:
        writer.write(f)

    print(f'PDF combinado guardado en: {pdf_combined_path}')

def mover_pdfs_a_carpeta(ruta_base, mover=True):
    if not mover:
        return ruta_base

    ruta_pdfs = os.path.join(ruta_base)
    ruta_pdfs_combinados = os.path.join(ruta_base, 'pdfs_combinados')
    os.makedirs(ruta_pdfs_combinados, exist_ok=True)

    pdfs = [f for f in os.listdir(ruta_pdfs) if f.endswith('.pdf')]
    print(f'PDFs encontrados para mover: {pdfs}')

    for pdf in pdfs:
        pdf_path = os.path.join(ruta_pdfs, pdf)
        print(f'Moviendo PDF: {pdf_path} a {ruta_pdfs_combinados}')
        shutil.move(pdf_path, os.path.join(ruta_pdfs_combinados, pdf))

    return ruta_pdfs_combinados

def procesar_dataset(ruta_dataset, anime_name, descargar_imagenes=True, crear_pdfs=True):
    dataset = pd.read_csv(ruta_dataset)

    for _, row in dataset.iterrows():
        capitulo = row['capitulo']
        paginas = ast.literal_eval(row['paginas'])
        ruta_capitulo = os.path.join('MANGAS', anime_name, f'capitulo_{capitulo}')
        
        if descargar_imagenes:
            for i, pagina in enumerate(paginas):
                url_imagen = pagina['imagen']
                print(f'Descargando imagen {i+1}/{len(paginas)} para el capítulo {capitulo}: {url_imagen}')
                ruta_imagen = descargar_imagen(ruta_capitulo, url_imagen, i+1)
        
        if crear_pdfs:
            lista_imagenes = [os.path.join(ruta_capitulo, f'{i+1}.jpg') for i in range(len(paginas))]
            crear_pdf(ruta_capitulo, lista_imagenes, anime_name, capitulo)

def procesar_url(url_manga, descargar_imagenes, crear_pdfs, mover_pdfs, combinar_pdfs_flag):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    anime_name = extract_anime_name(url_manga)
    ruta_base = os.path.join('MANGAS', anime_name)
    ruta_dataset = os.path.join(ruta_base, 'dataset.csv')
    procesar_dataset(ruta_dataset, anime_name, descargar_imagenes, crear_pdfs)

    if mover_pdfs:
        ruta_pdfs_combinados = mover_pdfs_a_carpeta(ruta_base)
    else:
        ruta_pdfs_combinados = ruta_base

    if combinar_pdfs_flag:
        combinar_pdfs(ruta_pdfs_combinados, anime_name)

def ejecutar_proceso():
    urls_text = text_area.get("1.0", tk.END).strip()
    urls_manga = urls_text.split('\n')

    descargar_imagenes = var_descargar_imagenes.get()
    crear_pdfs = var_crear_pdfs.get()
    mover_pdfs = var_mover_pdfs.get()
    combinar_pdfs_flag = var_combinar_pdfs.get()

    for url in urls_manga:
        if url:
            try:
                procesar_url(url, descargar_imagenes, crear_pdfs, mover_pdfs, combinar_pdfs_flag)
                messagebox.showinfo("Proceso completado", f"Proceso completado para la URL: {url}")
            except Exception as e:
                messagebox.showerror("Error", f"Error al procesar la URL: {url}\n{str(e)}")

root = tk.Tk()
root.title("Procesador de Manga")
root.geometry("600x600")

label = tk.Label(root, text="Ingrese las URLs de los mangas (una por línea):")
label.pack(pady=10)

text_area = scrolledtext.ScrolledText(root, width=70, height=10)
text_area.pack(pady=10)

frame = tk.Frame(root)
frame.pack(pady=10)

var_descargar_imagenes = BooleanVar()
check_descargar_imagenes = Checkbutton(frame, text="Descargar Imágenes", variable=var_descargar_imagenes)
check_descargar_imagenes.grid(row=0, column=0, padx=5, pady=5)

var_crear_pdfs = BooleanVar()
check_crear_pdfs = Checkbutton(frame, text="Crear PDFs", variable=var_crear_pdfs)
check_crear_pdfs.grid(row=0, column=1, padx=5, pady=5)

var_mover_pdfs = BooleanVar()
check_mover_pdfs = Checkbutton(frame, text="Mover PDFs a Carpeta", variable=var_mover_pdfs)
check_mover_pdfs.grid(row=1, column=0, padx=5, pady=5)

var_combinar_pdfs = BooleanVar()
check_combinar_pdfs = Checkbutton(frame, text="Combinar PDFs", variable=var_combinar_pdfs)
check_combinar_pdfs.grid(row=1, column=1, padx=5, pady=5)

button = tk.Button(root, text="Ejecutar", command=ejecutar_proceso)
button.pack(pady=20)

root.mainloop()
