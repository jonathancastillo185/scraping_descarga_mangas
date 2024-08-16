import os
import tkinter as tk
from tkinter import scrolledtext, messagebox, Toplevel
from download import *

# Configuración de estilos
DARK_BG = "#2b2b2b"
LIGHT_BG = "#3c3f41"
TEXT_COLOR = "#ffffff"
BUTTON_BG = "#555555"
HIGHLIGHT_COLOR = "#3c8dbc"
FONT = ("Roboto", 10)

cancelar_proceso = False  # Variable para controlar la cancelación

def aplicar_tema(widget):
    """Aplica el tema oscuro a los widgets de Tkinter."""
    for child in widget.winfo_children():
        if isinstance(child, tk.Toplevel) or isinstance(child, tk.Frame):
            aplicar_tema(child)
        else:
            try:
                child.config(bg=DARK_BG, fg=TEXT_COLOR, font=FONT)
                if isinstance(child, tk.Button):
                    child.config(bg=BUTTON_BG, activebackground=HIGHLIGHT_COLOR)
                elif isinstance(child, tk.Entry) or isinstance(child, tk.Listbox) or isinstance(child, scrolledtext.ScrolledText):
                    child.config(bg=LIGHT_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR)
                elif isinstance(child, tk.Label):
                    child.config(bg=DARK_BG, fg=TEXT_COLOR, font=FONT)
            except tk.TclError:
                pass

def actualizar_lista_mangas():
    lista_mangas.delete(0, tk.END)
    mangas = obtener_mangas_descargados()
    for manga in mangas:
        lista_mangas.insert(tk.END, manga)

def mostrar_info_manga(event):
    seleccion = lista_mangas.curselection()
    if seleccion:
        manga_name = lista_mangas.get(seleccion)
        info = obtener_info_manga(manga_name)
        url_guardada = leer_url(os.path.join(os.getcwd(), "mangas", manga_name))

        text_info.delete(1.0, tk.END)
        text_info.insert(tk.END, f"Manga: {manga_name}\n\n")
        text_info.insert(tk.END, f"URL Guardada: {url_guardada if url_guardada else 'No disponible'}\n\n")
        text_info.insert(tk.END, f"Dataset: {'Sí' if info['dataset'] else 'No'}\n")
        text_info.insert(tk.END, f"Imágenes disponibles para capítulos: {', '.join(map(str, info['imagenes']))}\n")
        text_info.insert(tk.END, f"PDFs por capítulo: {len(info['pdfs'])}\n")
        text_info.insert(tk.END, f"PDFs combinados: {len(info['combinados'])}\n")

def combinar_pdfs_gui():
    seleccion = lista_mangas.curselection()
    if seleccion:
        manga_name = lista_mangas.get(seleccion)
        start = start_var.get()
        end = end_var.get()
        interval = interval_var.get()

        ruta_base = os.path.join(os.getcwd(), "mangas", manga_name, 'pdfs_combinados')
        if not os.path.exists(ruta_base):
            messagebox.showwarning("Error", "No hay PDFs para combinar en este manga.")
            return

        try:
            start = int(start) if start else None
            end = int(end) if end else None
            interval = int(interval) if interval else None
        except ValueError:
            messagebox.showerror("Error", "Rangos y intervalos deben ser números enteros.")
            return

        combinar_pdfs(ruta_base, manga_name, start=start, end=end, interval=interval)
        messagebox.showinfo("Combinación Completa", "Los PDFs se han combinado exitosamente.")

def abrir_ventana_descarga():
    ventana_descarga = Toplevel()
    ventana_descarga.title("Descargar Manga")
    ventana_descarga.config(bg=DARK_BG)
    aplicar_tema(ventana_descarga)

    def on_start_button_click():
        global cancelar_proceso
        cancelar_proceso = False
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
        threading.Thread(target=run_processes_controlled, args=(urls, crear_dataset_var, crear_pdfs_var, eliminar_imagenes_var, combinar_capitulos_var, overwrite_var)).start()

    def on_cancel_button_click():
        global cancelar_proceso
        cancelar_proceso = True
        messagebox.showinfo("Proceso Cancelado", "El proceso de descarga ha sido cancelado.")
    
    def cargar_url_guardada():
        seleccion = lista_mangas.curselection()
        if seleccion:
            manga_name = lista_mangas.get(seleccion)
            url_guardada = leer_url(os.path.join(os.getcwd(), "mangas", manga_name))
            if url_guardada:
                url_text.delete(1.0, tk.END)
                url_text.insert(tk.END, url_guardada)
            else:
                messagebox.showinfo("Sin URL Guardada", "No se encontró una URL guardada para este manga.")

    tk.Label(ventana_descarga, text="URLs del Anime (una por línea):").pack(pady=5)
    url_text = scrolledtext.ScrolledText(ventana_descarga, width=60, height=15)
    url_text.pack(pady=5)

    btn_cargar_url = tk.Button(ventana_descarga, text="Cargar URL Guardada", command=cargar_url_guardada)
    btn_cargar_url.pack(pady=5)

    var_crear_dataset = tk.BooleanVar(value=True)
    var_crear_pdfs = tk.BooleanVar(value=True)
    var_eliminar_imagenes = tk.BooleanVar(value=False)
    var_combinar_capitulos = tk.BooleanVar(value=True)
    var_overwrite = tk.BooleanVar(value=True)

    tk.Checkbutton(ventana_descarga, text="Crear Dataset", variable=var_crear_dataset).pack(pady=5)
    tk.Checkbutton(ventana_descarga, text="Crear PDFs", variable=var_crear_pdfs).pack(pady=5)
    tk.Checkbutton(ventana_descarga, text="Eliminar Imágenes", variable=var_eliminar_imagenes).pack(pady=5)
    tk.Checkbutton(ventana_descarga, text="Combinar Capítulos", variable=var_combinar_capitulos).pack(pady=5)
    tk.Checkbutton(ventana_descarga, text="Sobrescribir Archivos Existentes", variable=var_overwrite).pack(pady=5)

    start_button = tk.Button(ventana_descarga, text="Iniciar", command=on_start_button_click)
    start_button.pack(pady=10)

    cancel_button = tk.Button(ventana_descarga, text="Cancelar", command=on_cancel_button_click)
    cancel_button.pack(pady=5)

def run_processes_controlled(urls, crear_dataset_var, crear_pdfs_var, eliminar_imagenes_var, combinar_capitulos_var, overwrite_var):
    global cancelar_proceso
    clean_last_log()
    
    for url in urls:
        if cancelar_proceso:
            break
        procesar_url_controlled(url, crear_dataset_var, crear_pdfs_var, eliminar_imagenes_var, combinar_capitulos_var, overwrite_var)


def procesar_url_controlled(url, crear_dataset_var, crear_pdfs_var, eliminar_imagenes_var, combinar_capitulos_var, overwrite_var):
    global cancelar_proceso
    anime_name = extract_anime_name(url)
    base_path = os.path.join(os.getcwd(), "mangas", anime_name, "dataset")
    base_path_pdf_completo = os.path.join(os.getcwd(), "mangas", anime_name)
    csv_path = os.path.join(base_path, "capitulos_completos.csv")

    # Crear las rutas si no existen
    os.makedirs(base_path, exist_ok=True)
    os.makedirs(base_path_pdf_completo, exist_ok=True)

    # Guardar la URL del manga para usos futuros
    guardar_url(base_path_pdf_completo, url)
    
    if crear_dataset_var and not cancelar_proceso:
        crear_dataset(url, csv_path, overwrite_var)

    if crear_pdfs_var and not cancelar_proceso:
        procesar_dataset(csv_path, anime_name, crear_pdfs_var, eliminar_imagenes_var, overwrite=overwrite_var)
    
    if combinar_capitulos_var and not cancelar_proceso:
        ruta_pdfs_combinados = mover_pdfs_a_carpeta(base_path_pdf_completo)
        combinar_pdfs(ruta_pdfs_combinados, anime_name)


def start_gui():
    root = tk.Tk()
    root.title("Manga Downloader")
    root.config(bg=DARK_BG)

    global lista_mangas, text_info, start_var, end_var, interval_var

    frame_mangas = tk.Frame(root, bg=DARK_BG)
    frame_mangas.pack(side=tk.LEFT, padx=10, pady=10)

    tk.Label(frame_mangas, text="Mangas Descargados:").pack()

    lista_mangas = tk.Listbox(frame_mangas, width=30, height=20)
    lista_mangas.pack()
    lista_mangas.bind("<<ListboxSelect>>", mostrar_info_manga)

    btn_actualizar = tk.Button(frame_mangas, text="Actualizar Lista", command=actualizar_lista_mangas)
    btn_actualizar.pack(pady=5)

    btn_descargar = tk.Button(frame_mangas, text="Descargar Manga", command=abrir_ventana_descarga)
    btn_descargar.pack(pady=5)

    frame_info = tk.Frame(root, bg=DARK_BG)
    frame_info.pack(side=tk.RIGHT, padx=10, pady=10)

    text_info = scrolledtext.ScrolledText(frame_info, width=60, height=20)
    text_info.pack()

    tk.Label(frame_info, text="Combinar PDFs (rango de capítulos):").pack(pady=5)
    start_var = tk.StringVar()
    end_var = tk.StringVar()
    interval_var = tk.StringVar()

    tk.Label(frame_info, text="Inicio:").pack()
    tk.Entry(frame_info, textvariable=start_var).pack()

    tk.Label(frame_info, text="Fin:").pack()
    tk.Entry(frame_info, textvariable=end_var).pack()

    tk.Label(frame_info, text="Intervalo:").pack()
    tk.Entry(frame_info, textvariable=interval_var).pack()

    btn_combinar = tk.Button(frame_info, text="Combinar PDFs", command=combinar_pdfs_gui)
    btn_combinar.pack(pady=10)

    aplicar_tema(root)
    aplicar_tema(frame_mangas)  # Asegura que el tema se aplica también en el frame_mangas
    actualizar_lista_mangas()

    root.mainloop()

if __name__ == "__main__":
    start_gui()
