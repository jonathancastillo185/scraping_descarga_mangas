import os
import requests
import pandas as pd
import ast
import shutil
import tkinter as tk
from tkinter import scrolledtext, messagebox, Checkbutton, BooleanVar
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

def crear_pdf(ruta_guardado, lista_imagenes, anime_name, capitulo, eliminar_imagenes=False):
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

    if eliminar_imagenes:
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

def combinar_pdfs(ruta_pdfs_combinados, anime_name):
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

def mover_pdfs_a_carpeta(ruta_base):
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

def crear_csv(anime_name, driver):
    ruta_base = os.path.join('MANGAS', anime_name)
    os.makedirs(ruta_base, exist_ok=True)
    ruta_dataset = os.path.join(ruta_base, 'dataset.csv')

    driver.get(f"https://inmanga.com/ver/manga/{anime_name}")

    datos = []
    capitulos = driver.find_elements(By.CLASS_NAME, 'element')
    for capitulo in capitulos:
        capitulo_numero = capitulo.text.split()[1]  # Ajustar según el formato del texto
        capitulo_url = capitulo.get_attribute('href')
        driver.get(capitulo_url)
        
        paginas = driver.find_elements(By.CLASS_NAME, 'image-container')
        paginas_urls = [{"imagen": pagina.get_attribute('src')} for pagina in paginas]
        
        datos.append({"capitulo": capitulo_numero, "paginas": paginas_urls})

    df = pd.DataFrame(datos)
    df.to_csv(ruta_dataset, index=False)
    print(f'Dataset guardado en: {ruta_dataset}')

def descargar_imagenes_y_crear_pdfs(ruta_dataset, anime_name, descargar_imagenes=True, crear_pdfs=True, eliminar_imagenes=False):
    if not os.path.exists(ruta_dataset) or os.stat(ruta_dataset).st_size == 0:
        print(f'El archivo {ruta_dataset} está vacío o no existe.')
        return

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
            crear_pdf(ruta_capitulo, lista_imagenes, anime_name, capitulo, eliminar_imagenes)

def procesar_url(url_manga, crear_dataset, descargar_imagenes, crear_pdfs, mover_pdfs, combinar_pdfs_flag, eliminar_imagenes):
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    anime_name = extract_anime_name(url_manga)
    driver.get(url_manga)

    if crear_dataset:
        crear_csv(anime_name, driver)

    ruta_base = os.path.join('MANGAS', anime_name)
    ruta_dataset = os.path.join(ruta_base, 'dataset.csv')

    if descargar_imagenes or crear_pdfs:
        descargar_imagenes_y_crear_pdfs(ruta_dataset, anime_name, descargar_imagenes, crear_pdfs, eliminar_imagenes)

    if mover_pdfs:
        ruta_pdfs_combinados = mover_pdfs_a_carpeta(ruta_base)
    
    if combinar_pdfs_flag:
        combinar_pdfs(ruta_base, anime_name)
    
    driver.quit()

def main():
    urls = [
        'https://inmanga.com/ver/manga/Goblin-Slayer/1/a3ee5be2-18e2-4dac-8195-d6382e69487b',
        'https://inmanga.com/ver/manga/Goblin-Slayer/2/b04e16aa-8f43-49e5-a6a4-8573b12d23aa'
    ]

    root = tk.Tk()
    root.title("Descargador de Manga")

    text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=80, height=20)
    text_area.grid(column=0, row=0, columnspan=3, padx=10, pady=10)

    for url in urls:
        text_area.insert(tk.END, f'{url}\n')

    crear_dataset_var = BooleanVar()
    descargar_imagenes_var = BooleanVar()
    crear_pdfs_var = BooleanVar()
    mover_pdfs_var = BooleanVar()
    combinar_pdfs_var = BooleanVar()
    eliminar_imagenes_var = BooleanVar()

    Checkbutton(root, text="Crear Dataset", var=crear_dataset_var).grid(row=1, column=0, padx=10, pady=5)
    Checkbutton(root, text="Descargar Imágenes", var=descargar_imagenes_var).grid(row=1, column=1, padx=10, pady=5)
    Checkbutton(root, text="Crear PDFs", var=crear_pdfs_var).grid(row=1, column=2, padx=10, pady=5)
    Checkbutton(root, text="Mover PDFs a Carpeta", var=mover_pdfs_var).grid(row=2, column=0, padx=10, pady=5)
    Checkbutton(root, text="Combinar PDFs", var=combinar_pdfs_var).grid(row=2, column=1, padx=10, pady=5)
    Checkbutton(root, text="Eliminar Imágenes", var=eliminar_imagenes_var).grid(row=2, column=2, padx=10, pady=5)

    def iniciar_proceso():
        for url in urls:
            procesar_url(
                url,
                crear_dataset=crear_dataset_var.get(),
                descargar_imagenes=descargar_imagenes_var.get(),
                crear_pdfs=crear_pdfs_var.get(),
                mover_pdfs=mover_pdfs_var.get(),
                combinar_pdfs_flag=combinar_pdfs_var.get(),
                eliminar_imagenes=eliminar_imagenes_var.get()
            )
        messagebox.showinfo("Proceso Completo", "El proceso ha finalizado.")

    tk.Button(root, text="Iniciar Proceso", command=iniciar_proceso).grid(row=3, column=0, columnspan=3, pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()
