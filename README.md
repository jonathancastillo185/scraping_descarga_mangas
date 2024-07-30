# Proyecto de Gestión de Manga en PDF

Este proyecto proporciona una herramienta para convertir imágenes de capítulos de manga en archivos PDF, combinar estos archivos PDF en un solo documento y gestionar el proceso a través de una interfaz gráfica de usuario (GUI) construida con Tkinter.

## Descripción

El script de Python en este proyecto realiza las siguientes tareas:
1. Descarga imágenes de capítulos de manga desde URLs específicas.
2. Convierte estas imágenes en archivos PDF individuales.
3. Combina estos archivos PDF en un solo documento PDF.
4. Permite gestionar el proceso mediante una interfaz gráfica creada con Tkinter.

## Requisitos

Asegúrate de tener instaladas las siguientes dependencias antes de ejecutar el script:

- Python 3.8 o superior
- Tkinter (generalmente incluido con Python)
- Las siguientes bibliotecas de Python:

    ```text
    altgraph==0.17.4
    asgiref==3.8.1
    attrs==23.2.0
    beautifulsoup4==4.12.3
    certifi==2024.7.4
    cffi==1.16.0
    chardet==5.2.0
    charset-normalizer==3.3.2
    colorama==0.4.6
    comm==0.2.2
    debugpy==1.8.2
    decorator==5.1.1
    Django==5.0.7
    exceptiongroup==1.2.2
    executing==2.0.1
    fpdf==1.7.2
    h11==0.14.0
    idna==3.7
    image==1.5.33
    ipykernel==6.29.5
    ipython==8.26.0
    jedi==0.19.1
    jupyter_client==8.6.2
    jupyter_core==5.7.2
    macholib==1.16.3
    matplotlib-inline==0.1.7
    nest-asyncio==1.6.0
    numpy==2.0.1
    outcome==1.3.0.post0
    packaging==24.1
    pandas==2.2.2
    parso==0.8.4
    pillow==10.4.0
    platformdirs==4.2.2
    prompt_toolkit==3.0.47
    psutil==6.0.0
    pure_eval==0.2.3
    pycparser==2.22
    Pygments==2.18.0
    PyPDF2==3.0.1
    PySocks==1.7.1
    python-dateutil==2.9.0.post0
    python-dotenv==1.0.1
    pytz==2024.1
    pywin32==306
    pyzmq==26.0.3
    requests==2.32.3
    selenium==4.23.1
    six==1.16.0
    sniffio==1.3.1
    sortedcontainers==2.4.0
    soupsieve==2.5
    sqlparse==0.5.1
    stack-data==0.6.3
    tk==0.1.0
    tornado==6.4.1
    traitlets==5.14.3
    trio==0.26.0
    trio-websocket==0.11.1
    typing_extensions==4.12.2
    tzdata==2024.1
    urllib3==2.2.2
    wcwidth==0.2.13
    webdriver-manager==4.0.2
    websocket-client==1.8.0
    wsproto==1.2.0
    ```

Puedes instalar las dependencias usando el siguiente comando:

```bash
pip install -r requirements.txt

Instalación

    Clona este repositorio en tu máquina local:

    bash

git clone https://github.com/tu_usuario/tu_repositorio.git

Navega al directorio del proyecto:

bash

cd tu_repositorio

Instala las dependencias:

bash

    pip install -r requirements.txt

Uso

    Configura las URLs de los capítulos de manga: Modifica el script para incluir las URLs de los capítulos que deseas descargar.

    Ejecuta el script:

    bash

    python main.py

    Interfaz de usuario: Utiliza la interfaz gráfica proporcionada por Tkinter para gestionar las opciones de descarga y conversión.

Descripción del Código

    main.py: Este es el script principal que gestiona la descarga de imágenes, conversión a PDF y combinación de archivos PDF. También contiene la lógica para la interfaz gráfica de usuario.

    utils.py: Incluye funciones auxiliares para la descarga de imágenes, conversión y combinación de PDFs.

    gui.py: Contiene el código para la interfaz gráfica construida con Tkinter.

Ejemplos de Uso

    Descargar imágenes y convertir a PDF: Configura las URLs en el script y ejecuta main.py para iniciar el proceso.

    Combinar PDFs: Después de convertir los capítulos en PDF, el script los combinará en un solo archivo PDF.

Contribución

Si deseas contribuir a este proyecto, por favor sigue estos pasos:

    Haz un fork del repositorio.
    Crea una rama para tu característica o corrección de errores (git checkout -b feature/nueva-caracteristica).
    Realiza tus cambios y haz commit de ellos (git commit -am 'Añadir nueva característica').
    Empuja tu rama al repositorio (git push origin feature/nueva-caracteristica).
    Crea un Pull Request en GitHub.
