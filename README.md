# Suite de Herramientas para Procesamiento de Derechos de Agua

Este repositorio contiene una colección de cuatro programas independientes diseñados para automatizar el filtrado, la transformación de coordenadas y la unificación de datos de derechos de agua en Chile.

---

## Los Programas

La suite se compone de 4 herramientas ejecutables (`.exe`):

1.  **Filtrador y Exportador (`ProcesadorDeDatos.exe`):** Lee un archivo Excel masivo con derechos de agua, aplica una serie de filtros definidos por el usuario y exporta los resultados en tres archivos CSV (`1956.csv`, `1969.csv`, `1984.csv`).

2.  **Transformador 1956 a 1984 (`Convertidor1956.exe`):** Toma un archivo CSV con coordenadas en Datum PSAD56 y las convierte al estándar WGS 84.

3.  **Transformador 1969 a 1984 (`Convertidor1969.exe`):** Toma un archivo CSV con coordenadas en Datum SAD69 y las convierte al estándar WGS 84.

4.  **Unificador Final (`UnificadorFinal.exe`):** Combina los tres archivos (dos de ellos ya transformados) en un único reporte final en formato Excel (`.xlsx`).

---

## Flujo de Trabajo Recomendado (Paso a Paso)

Para obtener el reporte final, se deben usar los programas en el siguiente orden:

1.  ▶️ **Ejecutar `ProcesadorDeDatos.exe`**.
    * **Entrada:** El archivo Excel original (`Derechos_Concedidos_...`).
    * **Salida:** Generará los archivos `1956.csv`, `1969.csv` y `1984.csv` en la carpeta de destino que elijas.

2.  ▶️ **Ejecutar `Convertidor1956.exe`**.
    * **Entrada:** El archivo `1956.csv` generado en el paso anterior.
    * **Salida:** Un nuevo archivo con las coordenadas transformadas (ej. `1956_convertido.csv`).

3.  ▶️ **Ejecutar `Convertidor1969.exe`**.
    * **Entrada:** El archivo `1969.csv` generado en el paso 1.
    * **Salida:** Un nuevo archivo con las coordenadas transformadas (ej. `1969_convertido.csv`).

4.  ▶️ **Ejecutar `UnificadorFinal.exe`**.
    * **Entradas:** Te pedirá seleccionar los tres archivos necesarios:
        1.  El `1984.csv` original del paso 1.
        2.  El `1956_convertido.csv` del paso 2.
        3.  El `1969_convertido.csv` del paso 3.
    * **Salida:** El archivo Excel (`.xlsx`) final con todos los datos unificados y en el sistema de coordenadas correcto (WGS 84).

---

## Requisitos del Archivo Excel de Origen

Para que el primer programa (`ProcesadorDeDatos.exe`) funcione correctamente, el archivo Excel de origen debe cumplir con las siguientes especificaciones:

### Formato y Estructura
* **Formato de Archivo:** Compatible con `.xlsx` (moderno) y `.xls` (antiguo).
* **Ubicación de Encabezados:** Los títulos de las columnas **deben estar obligatoriamente en la Fila 7**.

### Columnas Requeridas
Las siguientes columnas son utilizadas por el programa y deben tener el **nombre exacto** que se muestra a continuación, incluyendo los saltos de línea dentro de la celda.

| Nombre Exacto del Encabezado en Excel | Descripción |
| :--- | :--- |
| `Código de`<br>`Expediente` | Identificador único del expediente. |
| `Comuna` | Comuna a la que pertenece el derecho de agua. |
| `Tipo Derecho` | Clasificación del derecho (ej. Consuntivo). |
| `Naturaleza del Agua`| Origen del agua (ej. Subterranea). |
| `Caudal`<br>`Anual`<br>`Prom` | Valor numérico del caudal para el filtro opcional. |
| `UTM`<br>`Norte`<br>`Captación`<br>`(m)` | Coordenada UTM Norte. Debe ser un valor numérico. |
| `UTM`<br>`Este`<br>`Captación`<br>`(m)`| Coordenada UTM Este. Debe ser un valor numérico. |
| `Datum` | Sistema de referencia (debe contener "1956", "1969" o "1984"). |

---

## Para Modificar o Ejecutar el Código Fuente

Si deseas modificar o ejecutar el código fuente (/base_code/`.py`):

1.  **Entorno:** Asegúrate de tener Python 3.9 o superior.
2.  **Dependencias:** Instala todas las librerías necesarias ejecutando:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Generar Ejecutables:** Para crear los archivos `.exe`, utiliza la herramienta PyInstaller. Por ejemplo:
    ```bash
    pyinstaller --name "ProcesadorDeDatos" --onefile --windowed --icon="icono.ico" procesar_gui.py
    ```