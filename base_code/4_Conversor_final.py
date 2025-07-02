import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
import os

def procesar_y_combinar(rutas: dict, log_queue: queue.Queue):
    """
    Función que contiene toda la lógica de procesamiento de archivos.
    Se ejecuta en un hilo separado para no congelar la interfaz.
    """
    try:
        log_queue.put("\n🔄 Cargando y procesando archivos...")

        # Cargar y filtrar el archivo base 1984
        df_84 = pd.read_csv(rutas['1984'], sep=';', dtype={'Expediente': str})
        condicion_mantener = df_84['Datum'].notna() & (df_84['Datum'].astype(str).str.strip() != '')
        df_84_filtrado = df_84[condicion_mantener]
        log_queue.put(f"   - Se cargaron {len(df_84_filtrado)} registros válidos desde el archivo base 1984.")

        # Cargar los archivos ya convertidos
        df_56_convertido = pd.read_csv(rutas['56_conv'], sep=';', dtype={'Expediente': str})
        log_queue.put(f"   - Se cargaron {len(df_56_convertido)} registros desde el archivo convertido de 1956.")

        df_69_convertido = pd.read_csv(rutas['69_conv'], sep=';', dtype={'Expediente': str})
        log_queue.put(f"   - Se cargaron {len(df_69_convertido)} registros desde el archivo convertido de 1969.")

        # Combinar los tres DataFrames
        df_final = pd.concat([df_84_filtrado, df_56_convertido, df_69_convertido], ignore_index=True)
        log_queue.put(f"\n✅ Combinación inicial completa. Total de filas: {len(df_final)}")
        
        # Estandarizar la columna Datum a '1984'
        df_final['Datum'] = 1984
        log_queue.put("   - Columna 'Datum' estandarizada a '1984'.")
        
        # Devolver el resultado a través de la cola
        log_queue.put({'dataframe_final': df_final})

    except Exception as e:
        log_queue.put(f"❌ Ocurrió un error: {e}")
        log_queue.put({'dataframe_final': None})


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Unificador de Archivos Datum")
        self.geometry("800x450")

        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure('TButton', font=('Helvetica', 10))
        self.style.configure('TLabel', font=('Helvetica', 10))
        self.style.configure('TLabelframe.Label', font=('Helvetica', 11, 'bold'))
        self.style.configure('Accent.TButton', font=('Helvetica', 10, 'bold'))

        # Variables
        self.ruta_1984 = tk.StringVar()
        self.ruta_56_convertido = tk.StringVar()
        self.ruta_69_convertido = tk.StringVar()
        self.log_queue = queue.Queue()
        self.dataframe_resultado = None

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.crear_widgets(main_frame)
        self.after(100, self.procesar_log_queue)

    def crear_widgets(self, parent):
        # --- Frame de Selección de Archivos ---
        files_frame = ttk.LabelFrame(parent, text="1. Cargar Archivos Requeridos", padding="10")
        files_frame.pack(fill=tk.X, pady=5)
        
        # Fila para archivo 1984
        ttk.Label(files_frame, text="Archivo 1984 Original:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(files_frame, textvariable=self.ruta_1984, state='readonly').grid(row=0, column=1, sticky=tk.EW, padx=5, pady=4)
        ttk.Button(files_frame, text="Explorar...", command=lambda: self.seleccionar_archivo(self.ruta_1984, "Seleccione el archivo 1984.csv ORIGINAL")).grid(row=0, column=2, padx=5)

        # Fila para archivo 1956 convertido
        ttk.Label(files_frame, text="Archivo 1956 Convertido:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(files_frame, textvariable=self.ruta_56_convertido, state='readonly').grid(row=1, column=1, sticky=tk.EW, padx=5, pady=4)
        ttk.Button(files_frame, text="Explorar...", command=lambda: self.seleccionar_archivo(self.ruta_56_convertido, "Seleccione el archivo 1956_a_1984.csv CONVERTIDO")).grid(row=1, column=2, padx=5)

        # Fila para archivo 1969 convertido
        ttk.Label(files_frame, text="Archivo 1969 Convertido:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(files_frame, textvariable=self.ruta_69_convertido, state='readonly').grid(row=2, column=1, sticky=tk.EW, padx=5, pady=4)
        ttk.Button(files_frame, text="Explorar...", command=lambda: self.seleccionar_archivo(self.ruta_69_convertido, "Seleccione el archivo 1969_a_1984.csv CONVERTIDO")).grid(row=2, column=2, padx=5)
        
        files_frame.columnconfigure(1, weight=1)

        # --- Frame de Procesamiento ---
        process_frame = ttk.Frame(parent, padding="10")
        process_frame.pack(fill=tk.X, pady=5)
        self.process_button = ttk.Button(process_frame, text="Unificar Archivos", command=self.iniciar_proceso, style='Accent.TButton')
        self.process_button.pack(pady=5)

        # --- Frame de Log ---
        log_frame = ttk.LabelFrame(parent, text="Registro de Actividad", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled', height=10, font=('Consolas', 9))
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def seleccionar_archivo(self, string_var, title):
        filepath = filedialog.askopenfilename(title=title, filetypes=(("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")))
        if filepath: string_var.set(filepath)

    def iniciar_proceso(self):
        rutas = {
            '1984': self.ruta_1984.get(),
            '56_conv': self.ruta_56_convertido.get(),
            '69_conv': self.ruta_69_convertido.get()
        }
        if not all(rutas.values()):
            messagebox.showwarning("Faltan Archivos", "Por favor, seleccione los tres archivos necesarios antes de continuar.")
            return

        self.process_button.config(state='disabled')
        self.log_area.config(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state='disabled')
        
        thread = threading.Thread(target=procesar_y_combinar, args=(rutas, self.log_queue))
        thread.start()

    def procesar_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                if isinstance(msg, dict) and 'dataframe_final' in msg:
                    self.dataframe_resultado = msg['dataframe_final']
                    self.finalizar_proceso()
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
        if self.dataframe_resultado is None:
            messagebox.showerror("Error", "El proceso falló. Revise el registro de actividad.")
            return

        output_path = filedialog.asksaveasfilename(
            title="Guardar archivo final combinado como...",
            defaultextension=".xlsx",
            filetypes=[("Archivo Excel", "*.xlsx")]
        )
        if output_path:
            try:
                self.dataframe_resultado.to_excel(output_path, index=False, engine='openpyxl')
                messagebox.showinfo("Proceso Completado", f"El archivo final se ha generado exitosamente con {len(self.dataframe_resultado)} registros.")
            except Exception as e:
                messagebox.showerror("Error al Guardar", f"No se pudo guardar el archivo:\n{e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()