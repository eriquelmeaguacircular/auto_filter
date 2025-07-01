import pandas as pd
import numpy as np
import re
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import queue
import os

# --- CONFIGURACIÓN DE COLUMNAS (del script original) ---
COL_EXPEDIENTE = 'Código de \nExpediente'
COL_COMUNA = 'Comuna'
COL_TIPO_DERECHO = 'Tipo Derecho'
COL_NATURALEZA = 'Naturaleza del Agua'
COL_CAUDAL = 'Caudal \nAnual\nProm'
COL_NORTE = 'UTM \nNorte \nCaptación\n(m)'
COL_ESTE = 'UTM \nEste \nCaptación\n(m)'
COL_DATUM = 'Datum'

# --- LÓGICA DE PROCESAMIENTO (del script original) ---
def cargar_datos(ruta_archivo: str, log_queue: queue.Queue) -> pd.DataFrame | None:
    log_queue.put(f"🔄 Cargando datos desde '{ruta_archivo}'...")
    try:
        df = pd.read_excel(ruta_archivo, header=6, usecols='A:BP')
        df.columns = df.columns.str.strip()
        log_queue.put("✅ Datos cargados exitosamente.")
        df.replace(['S/I', 's/i', 'S/D', 's/d'], np.nan, inplace=True)
        return df
    except FileNotFoundError:
        log_queue.put(f"❌ ERROR: El archivo no fue encontrado en la ruta: {ruta_archivo}")
        return None
    except Exception as e:
        log_queue.put(f"❌ ERROR: Ocurrió un error inesperado al cargar el archivo: {e}")
        log_queue.put("   Asegúrate de tener instaladas las librerías necesarias: pip install pandas openpyxl xlrd")
        return None

def filtrar_datos(df: pd.DataFrame, filtros: dict, log_queue: queue.Queue) -> pd.DataFrame:
    log_queue.put("\n🔄 Aplicando filtros...")
    df_filtrado = df.copy()

    if filtros['comuna']:
        log_queue.put(f"   - Aplicando filtro de Comuna: '{filtros['comuna']}'")
        df_filtrado = df_filtrado[df_filtrado[COL_COMUNA].str.contains(filtros['comuna'], case=False, na=False)]

    condicion_naturaleza = (
        df_filtrado[COL_NATURALEZA].str.contains(filtros['naturaleza'], case=False, na=False) |
        df_filtrado[COL_NATURALEZA].isnull()
    )
    df_filtrado = df_filtrado[condicion_naturaleza]

    df_filtrado = df_filtrado[df_filtrado[COL_TIPO_DERECHO].str.contains(filtros['tipo_derecho'], case=False, na=False)]

    if filtros['caudal']:
        match = re.match(r'^\s*([<>=!]+)\s*(\d+\.?\d*)\s*$', filtros['caudal'])
        if match:
            operador = match.group(1)
            valor = float(match.group(2))
            caudal_numerico = pd.to_numeric(df_filtrado[COL_CAUDAL], errors='coerce')
            log_queue.put(f"   - Aplicando filtro de caudal: {COL_CAUDAL.replace(chr(10), ' ')} {operador} {valor}")
            if operador == '<=':
                df_filtrado = df_filtrado[caudal_numerico <= valor]
            elif operador == '>=':
                df_filtrado = df_filtrado[caudal_numerico >= valor]
            elif operador == '<':
                df_filtrado = df_filtrado[caudal_numerico < valor]
            elif operador == '>':
                df_filtrado = df_filtrado[caudal_numerico > valor]
            elif operador in ('==', '='):
                df_filtrado = df_filtrado[caudal_numerico == valor]
            elif operador == '!=':
                 df_filtrado = df_filtrado[caudal_numerico != valor]
            else:
                log_queue.put(f"⚠️ Advertencia: Operador de caudal '{operador}' no reconocido. Se omitirá este filtro.")
        else:
            log_queue.put("⚠️ Advertencia: Formato de filtro de caudal no válido. Se omitirá este filtro.")

    log_queue.put(f"✅ Filtro aplicado. Se encontraron {len(df_filtrado)} registros.")
    return df_filtrado

def estandarizar_coordenada(coord: float, digitos: int) -> str:
    if pd.isna(coord) or coord == 0:
        return ""
    s = str(int(coord))
    if len(s) > digitos:
        return s[:digitos]
    else:
        return s.ljust(digitos, '0')

def procesar_coordenadas(df: pd.DataFrame, log_queue: queue.Queue) -> pd.DataFrame:
    log_queue.put("\n🔄 Procesando coordenadas...")
    df_procesado = df.copy()
    df_procesado[COL_NORTE] = pd.to_numeric(df_procesado[COL_NORTE], errors='coerce')
    df_procesado[COL_ESTE] = pd.to_numeric(df_procesado[COL_ESTE], errors='coerce')
    condicion_eliminar = (df_procesado[COL_NORTE].fillna(0) == 0) & (df_procesado[COL_ESTE].fillna(0) == 0)
    n_eliminados = condicion_eliminar.sum()
    df_procesado = df_procesado[~condicion_eliminar]
    if n_eliminados > 0:
        log_queue.put(f"   - Se eliminaron {n_eliminados} filas con coordenadas nulas o cero.")
    df_procesado[COL_NORTE] = df_procesado[COL_NORTE].apply(lambda x: estandarizar_coordenada(x, 7))
    df_procesado[COL_ESTE] = df_procesado[COL_ESTE].apply(lambda x: estandarizar_coordenada(x, 6))
    log_queue.put("✅ Coordenadas procesadas y estandarizadas.")
    return df_procesado

def exportar_por_datum(df: pd.DataFrame, log_queue: queue.Queue, carpeta_destino: str):
    log_queue.put(f"\n🔄 Exportando archivos a la carpeta: {carpeta_destino}...")
    columnas_a_exportar = [COL_EXPEDIENTE, COL_NORTE, COL_ESTE, COL_DATUM]
    renombrar_columnas = {
        COL_EXPEDIENTE: 'Expediente',
        COL_NORTE: 'Norte',
        COL_ESTE: 'Este',
        COL_DATUM: 'Datum'
    }
    # --- LÍNEA CORREGIDA ---
    # Se cambió COL_DUATOSM por la variable correcta: COL_DATUM
    df[COL_DATUM] = df[COL_DATUM].astype(str)
    
    datums_a_exportar = {
        '1956': '1956.csv',
        '1969': '1969.csv',
        '1984': '1984.csv'
    }
    
    archivos_generados = 0
    for datum_val, nombre_archivo in datums_a_exportar.items():
        try:
            condicion_datum = (
                df[COL_DATUM].str.contains(datum_val, case=False) |
                df[COL_DATUM].str.lower().isin(['nan', 'none', '<na>'])
            )
            df_datum = df[condicion_datum]
            if not df_datum.empty:
                df_exportar = df_datum[columnas_a_exportar].rename(columns=renombrar_columnas)
                
                ruta_salida = os.path.join(carpeta_destino, nombre_archivo)
                
                df_exportar.to_csv(ruta_salida, index=False, encoding='utf-8-sig', sep=';')
                log_queue.put(f"   - ✅ Archivo '{nombre_archivo}' generado exitosamente.")
                archivos_generados += 1
            else:
                log_queue.put(f"   - ⚠️ No se encontraron registros para Datum '{datum_val}' (o vacíos).")
        
        except Exception as e:
            log_queue.put(f"   - ❌ ERROR al exportar el archivo '{nombre_archivo}': {e}")

    log_queue.put(f"FIN_PROCESO_EXITO:{archivos_generados}")

# --- INTERFAZ GRÁFICA ---
# --- INTERFAZ GRÁFICA ---
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Procesador de Derechos de Agua")
        self.geometry("800x650")

        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure('TButton', font=('Helvetica', 10))
        self.style.configure('TLabel', font=('Helvetica', 10))
        self.style.configure('TEntry', font=('Helvetica', 10))
        self.style.configure('TLabelframe.Label', font=('Helvetica', 11, 'bold'))
        self.style.configure('Accent.TButton', font=('Helvetica', 10, 'bold'))

        # Variables
        self.ruta_archivo = tk.StringVar()
        self.ruta_destino = tk.StringVar()
        self.comuna = tk.StringVar()
        self.naturaleza = tk.StringVar()
        self.tipo_derecho = tk.StringVar()
        self.caudal_operador = tk.StringVar()
        self.caudal_valor = tk.StringVar()
        self.log_queue = queue.Queue()

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.crear_widgets(main_frame)
        self.after(100, self.procesar_log_queue)

    def crear_widgets(self, parent):
        # --- Frame de Selección de Archivos ---
        io_frame = ttk.LabelFrame(parent, text="1. Archivos de Entrada y Salida", padding="10")
        io_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(io_frame, text="Archivo Excel:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(io_frame, textvariable=self.ruta_archivo, state='readonly').grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(io_frame, text="Explorar...", command=self.seleccionar_archivo).grid(row=0, column=2, padx=5)

        ttk.Label(io_frame, text="Carpeta Destino:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(io_frame, textvariable=self.ruta_destino, state='readonly').grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(io_frame, text="Explorar...", command=self.seleccionar_destino).grid(row=1, column=2, padx=5)
        io_frame.columnconfigure(1, weight=1)

        # --- Frame de Filtros ---
        filters_frame = ttk.LabelFrame(parent, text="2. Criterios de Filtrado", padding="10")
        filters_frame.pack(fill=tk.X, pady=5)

        ttk.Label(filters_frame, text="Comuna (opcional):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        ttk.Entry(filters_frame, textvariable=self.comuna).grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=3)

        ttk.Label(filters_frame, text="Naturaleza del Agua:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        naturaleza_options = ['Subterranea', 'Superficial y Corriente', 'Superficial']
        ttk.Combobox(filters_frame, textvariable=self.naturaleza, values=naturaleza_options, state='readonly').grid(row=1, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=3)

        ttk.Label(filters_frame, text="Tipo de Derecho:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=3)
        derecho_options = ['Consuntivo', 'No consuntivo']
        ttk.Combobox(filters_frame, textvariable=self.tipo_derecho, values=derecho_options, state='readonly').grid(row=2, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=3)
        
        ttk.Label(filters_frame, text="Filtro de Caudal:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=3)
        caudal_operators = ['Mayor que', 'Mayor o igual que', 'Menor que', 'Menor o igual que', 'Igual a']
        ttk.Combobox(filters_frame, textvariable=self.caudal_operador, values=caudal_operators, state='readonly', width=18).grid(row=3, column=1, sticky=tk.W, padx=5, pady=3)
        ttk.Entry(filters_frame, textvariable=self.caudal_valor).grid(row=3, column=2, sticky=tk.EW, padx=5, pady=3)

        filters_frame.columnconfigure(2, weight=1)

        # --- Frame de Procesamiento ---
        process_frame = ttk.Frame(parent, padding="10")
        process_frame.pack(fill=tk.X, pady=5)

        # Frame interno para los botones
        button_frame = ttk.Frame(process_frame)
        button_frame.pack(fill=tk.X)

        self.process_button = ttk.Button(button_frame, text="Iniciar Procesamiento", command=self.iniciar_procesamiento, style='Accent.TButton')
        self.process_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,5))

        # NUEVO BOTÓN "LIMPIAR"
        self.clear_button = ttk.Button(button_frame, text="Limpiar Campos", command=self.limpiar_campos)
        self.clear_button.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5,0))
        
        self.progress_bar = ttk.Progressbar(process_frame, orient='horizontal', mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(10, 5))

        # --- Frame de Log ---
        log_frame = ttk.LabelFrame(parent, text="Registro de Actividad", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled', height=10, font=('Consolas', 9))
        self.log_area.pack(fill=tk.BOTH, expand=True)
    
    # NUEVA FUNCIÓN PARA LIMPIAR LA INTERFAZ
    def limpiar_campos(self):
        """Resetea todos los campos de entrada y el área de registro."""
        self.ruta_archivo.set("")
        self.ruta_destino.set("")
        self.comuna.set("")
        self.naturaleza.set("")
        self.tipo_derecho.set("")
        self.caudal_operador.set("")
        self.caudal_valor.set("")
        self.progress_bar['value'] = 0

        # Limpiar el área de registro
        self.log_area.config(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.insert(tk.END, "Campos limpiados. Listo para un nuevo proceso.\n")
        self.log_area.config(state='disabled')

    def seleccionar_archivo(self):
        filepath = filedialog.askopenfilename(title="Seleccionar archivo Excel", filetypes=(("Archivos de Excel", "*.xlsx *.xls"), ("Todos los archivos", "*.*")))
        if filepath: self.ruta_archivo.set(filepath)

    def seleccionar_destino(self):
        folderpath = filedialog.askdirectory(title="Seleccionar carpeta de destino para los CSV")
        if folderpath: self.ruta_destino.set(folderpath)

    def iniciar_procesamiento(self):
        if not self.ruta_archivo.get() or not self.ruta_destino.get():
            tk.messagebox.showwarning("Advertencia", "Debe seleccionar un archivo de Excel y una carpeta de destino.")
            return

        caudal_str = ""
        op_map = {'Mayor que': '>', 'Mayor o igual que': '>=', 'Menor que': '<', 'Menor o igual que': '<=', 'Igual a': '=='}
        if self.caudal_operador.get() and self.caudal_valor.get():
            try:
                float(self.caudal_valor.get())
                caudal_str = f"{op_map[self.caudal_operador.get()]} {self.caudal_valor.get()}"
            except ValueError:
                tk.messagebox.showerror("Error", "El valor del caudal debe ser numérico.")
                return

        filtros = {
            "comuna": self.comuna.get(), "naturaleza": self.naturaleza.get(),
            "tipo_derecho": self.tipo_derecho.get(), "caudal": caudal_str
        }

        if not filtros['naturaleza'] or not filtros['tipo_derecho']:
            tk.messagebox.showwarning("Advertencia", "'Naturaleza del Agua' y 'Tipo de Derecho' son campos obligatorios.")
            return

        self.process_button.config(state='disabled')
        self.clear_button.config(state='disabled') # Deshabilitar también al procesar
        self.log_area.config(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state='disabled')
        self.progress_bar['value'] = 0

        thread = threading.Thread(target=self.proceso_en_hilo, args=(self.ruta_archivo.get(), self.ruta_destino.get(), filtros))
        thread.start()

    def proceso_en_hilo(self, ruta_archivo, ruta_destino, filtros):
        self.progress_bar['value'] = 10
        df_original = cargar_datos(ruta_archivo, self.log_queue)
        if df_original is None:
            self.finalizar_proceso()
            return
        self.progress_bar['value'] = 25

        df_filtrado = filtrar_datos(df_original, filtros, self.log_queue)
        if df_filtrado.empty:
            self.log_queue.put("FIN_PROCESO_SIN_DATOS")
            self.finalizar_proceso()
            return
        self.progress_bar['value'] = 50

        df_procesado = procesar_coordenadas(df_filtrado, self.log_queue)
        if df_procesado.empty:
            self.log_queue.put("FIN_PROCESO_SIN_DATOS")
            self.finalizar_proceso()
            return
        self.progress_bar['value'] = 75

        exportar_por_datum(df_procesado, self.log_queue, ruta_destino)
        self.progress_bar['value'] = 100
        self.finalizar_proceso()

    def finalizar_proceso(self):
        self.process_button.config(state='normal')
        self.clear_button.config(state='normal') # Volver a habilitar

    def procesar_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                if isinstance(msg, str) and msg.startswith("FIN_PROCESO_EXITO:"):
                    num_archivos = msg.split(":")[1]
                    tk.messagebox.showinfo("Proceso Completado", f"¡Proceso finalizado!\nSe generaron {num_archivos} archivos en la carpeta de destino.")
                elif msg == "FIN_PROCESO_SIN_DATOS":
                     tk.messagebox.showinfo("Proceso Finalizado", "El proceso terminó pero no se encontraron registros que cumplan los criterios para exportar.")
                else:
                    self.log_area.config(state='normal')
                    self.log_area.insert(tk.END, str(msg) + '\n')
                    self.log_area.config(state='disabled')
                    self.log_area.see(tk.END)
        except queue.Empty:
            pass
        self.after(100, self.procesar_log_queue)

if __name__ == "__main__":
    app = App()
    app.mainloop()