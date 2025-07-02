import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import queue
import pyproj

# --- CONFIGURACIÓN DE SISTEMAS DE REFERENCIA (CRS) ---
CRS_ORIGEN = "EPSG:24819"  # SAD69 / UTM zone 19S
CRS_DESTINO = "EPSG:32719" # WGS 84 / UTM zone 19S

def proceso_de_transformacion(ruta_entrada: str, ruta_salida: str, log_queue: queue.Queue):
    """
    Función principal de procesamiento que se ejecuta en un hilo separado.
    """
    try:
        log_queue.put(f"🔄 Procesando archivo: {ruta_entrada.split('/')[-1]}")
        df = pd.read_csv(ruta_entrada, sep=';', dtype={'Expediente': str})
        
        # 1. Filtrar por Datum no vacío y que contenga '1969'
        df.dropna(subset=['Datum'], inplace=True)
        df_filtrado = df[df['Datum'].astype(str).str.contains('1969', case=False)]

        if df_filtrado.empty:
            log_queue.put("⏹️ No se encontraron registros con Datum 1969 para procesar.")
            log_queue.put("FIN_SIN_DATOS")
            return

        # 2. Asegurar que las coordenadas son numéricas y eliminar filas inválidas o con ceros
        df_filtrado['Norte'] = pd.to_numeric(df_filtrado['Norte'], errors='coerce')
        df_filtrado['Este'] = pd.to_numeric(df_filtrado['Este'], errors='coerce')
        df_filtrado.dropna(subset=['Norte', 'Este'], inplace=True)
        df_filtrado = df_filtrado[(df_filtrado['Norte'] != 0) & (df_filtrado['Este'] != 0)]
        
        # 3. Transformar
        log_queue.put(f"   - Transformando {len(df_filtrado)} registros desde {CRS_ORIGEN}...")
        transformer = pyproj.Transformer.from_crs(pyproj.CRS(CRS_ORIGEN), pyproj.CRS(CRS_DESTINO), always_xy=True)
        este_transformado, norte_transformado = transformer.transform(df_filtrado['Este'].values, df_filtrado['Norte'].values)
        
        norte_transformado[np.isinf(norte_transformado)] = np.nan
        este_transformado[np.isinf(este_transformado)] = np.nan

        df_filtrado['Este'] = este_transformado
        df_filtrado['Norte'] = norte_transformado
        df_filtrado.dropna(subset=['Norte', 'Este'], inplace=True)

        if df_filtrado.empty:
            log_queue.put("⏹️ Ningún registro pudo ser transformado exitosamente.")
            log_queue.put("FIN_CON_ERROR")
            return

        # 4. Finalizar y guardar
        df_filtrado['Norte'] = df_filtrado['Norte'].round(0).astype(np.int64)
        df_filtrado['Este'] = df_filtrado['Este'].round(0).astype(np.int64)
        df_filtrado['Datum'] = 'WGS 84'

        df_filtrado.to_csv(ruta_salida, index=False, sep=';')
        log_queue.put(f"✅ Se procesaron y transformaron {len(df_filtrado)} registros.")
        log_queue.put(f"✨ ¡Éxito! Archivo guardado en: {ruta_salida.split('/')[-1]}")
        log_queue.put(f"FIN_CON_EXITO:{len(df_filtrado)}")

    except Exception as e:
        log_queue.put(f"❌ Ocurrió un error: {e}")
        log_queue.put("FIN_CON_ERROR")

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Convertidor de Datum 1969 a 1984")
        self.geometry("800x400")

        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure('TButton', font=('Helvetica', 10))
        self.style.configure('TLabel', font=('Helvetica', 10))
        self.style.configure('TLabelframe.Label', font=('Helvetica', 11, 'bold'))
        self.style.configure('Accent.TButton', font=('Helvetica', 10, 'bold'))

        self.ruta_entrada = tk.StringVar()
        self.ruta_salida = tk.StringVar()
        self.log_queue = queue.Queue()

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        self.crear_widgets(main_frame)
        self.after(100, self.procesar_log_queue)

    def crear_widgets(self, parent):
        io_frame = ttk.LabelFrame(parent, text="Selección de Archivos", padding="10")
        io_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(io_frame, text="Archivo de Entrada (1969):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(io_frame, textvariable=self.ruta_entrada, state='readonly').grid(row=0, column=1, sticky=tk.EW, padx=5, pady=4)
        ttk.Button(io_frame, text="Explorar...", command=self.seleccionar_entrada).grid(row=0, column=2, padx=5)

        ttk.Label(io_frame, text="Archivo de Salida (Convertido):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(io_frame, textvariable=self.ruta_salida, state='readonly').grid(row=1, column=1, sticky=tk.EW, padx=5, pady=4)
        ttk.Button(io_frame, text="Guardar como...", command=self.seleccionar_salida).grid(row=1, column=2, padx=5)
        
        io_frame.columnconfigure(1, weight=1)

        process_frame = ttk.Frame(parent, padding="10")
        process_frame.pack(fill=tk.X, pady=5)
        button_frame = ttk.Frame(process_frame)
        button_frame.pack(fill=tk.X)
        self.process_button = ttk.Button(button_frame, text="Iniciar Transformación", command=self.iniciar_proceso, style='Accent.TButton')
        self.process_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,5))
        self.clear_button = ttk.Button(button_frame, text="Limpiar", command=self.limpiar_campos)
        self.clear_button.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5,0))
        
        log_frame = ttk.LabelFrame(parent, text="Registro de Actividad", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled', height=10, font=('Consolas', 9))
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def seleccionar_entrada(self):
        filepath = filedialog.askopenfilename(title="Seleccione el archivo CSV con Datum 1969", filetypes=(("Archivos CSV", "*.csv"),))
        if filepath: self.ruta_entrada.set(filepath)

    def seleccionar_salida(self):
        filepath = filedialog.asksaveasfilename(title="Guardar archivo transformado como...", defaultextension=".csv", filetypes=(("Archivos CSV", "*.csv"),))
        if filepath: self.ruta_salida.set(filepath)

    def limpiar_campos(self):
        self.ruta_entrada.set("")
        self.ruta_salida.set("")
        self.log_area.config(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.insert(tk.END, "Campos limpiados. Listo para un nuevo proceso.\n")
        self.log_area.config(state='disabled')

    def iniciar_proceso(self):
        if not self.ruta_entrada.get() or not self.ruta_salida.get():
            messagebox.showwarning("Faltan Archivos", "Debe seleccionar un archivo de entrada y una ubicación de salida.")
            return

        self.process_button.config(state='disabled')
        self.clear_button.config(state='disabled')
        self.log_area.config(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state='disabled')

        thread = threading.Thread(target=proceso_de_transformacion, args=(self.ruta_entrada.get(), self.ruta_salida.get(), self.log_queue))
        thread.start()

    def procesar_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                if isinstance(msg, str) and msg.startswith("FIN_CON_EXITO:"):
                    self.finalizar_proceso()
                    num_reg = msg.split(":")[1]
                    messagebox.showinfo("Proceso Completado", f"¡Transformación finalizada!\nSe generó un archivo con {num_reg} registros.")
                elif msg == "FIN_SIN_DATOS":
                    self.finalizar_proceso()
                    messagebox.showinfo("Proceso Finalizado", "No se encontraron registros válidos para procesar.")
                elif msg == "FIN_CON_ERROR":
                     self.finalizar_proceso()
                     messagebox.showerror("Error", "El proceso falló. Revise el registro de actividad.")
                else:
                    self.log_area.config(state='normal')
                    self.log_area.insert(tk.END, str(msg) + '\n')
                    self.log_area.config(state='disabled')
                    self.log_area.see(tk.END)
        except queue.Empty:
            pass
        self.after(100, self.procesar_log_queue)

    def finalizar_proceso(self):
        self.process_button.config(state='normal')
        self.clear_button.config(state='normal')

if __name__ == "__main__":
    app = App()
    app.mainloop()