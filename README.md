# Procesador de Derechos de Agua

## Descripción
Este programa es una herramienta diseñada para filtrar, procesar y exportar datos de derechos de agua desde un archivo Excel, generando archivos CSV limpios y estandarizados.

## Requisitos del Archivo Excel

### 1. Formato del Archivo
El programa es compatible con los siguientes formatos:
- `.xlsx` (formato moderno)
- `.xls` (formato de compatibilidad 97-2003)

### 2. Estructura de la Hoja de Cálculo
- **Ubicación de los Encabezados**: Los títulos deben estar en la Fila 7 de la hoja de cálculo
- **Rango de Datos**: Lectura desde columna A hasta BP
- Las filas 1-6 pueden contener información adicional (serán ignoradas)

### 3. Nombres de Columna Requeridos
Los siguientes encabezados deben existir en la Fila 7 con el formato exacto:

| Nombre del Encabezado | Descripción |
|----------------------|-------------|
| Código de <br/> Expediente | Identificador único del expediente |
| Comuna | Comuna a la que pertenece el derecho de agua |
| Tipo Derecho | Clasificación del derecho (ej. Consuntivo) |
| Naturaleza del Agua | Origen del agua (ej. Subterranea) |
| Caudal <br/> Anual <br/> Prom | Valor numérico del caudal para el filtro opcional |
| UTM <br/> Norte <br/> Captación <br/> (m) | Coordenada UTM Norte. Debe ser un valor numérico |
| UTM <br/> Este <br/> Captación <br/> (m) | Coordenada UTM Este. Debe ser un valor numérico |
| Datum | Sistema de referencia geodésico (debe contener "1956", "1969" o "1984") |

> **Nota**: Los encabezados con saltos de línea deben estar formateados usando Alt + Enter en Excel

## Uso del Programa

1. **Seleccionar Archivo de Entrada**
   - Clic en "Explorar..." para elegir el archivo Excel

2. **Seleccionar Carpeta de Destino**
   - Elegir ubicación para guardar los archivos CSV generados

3. **Completar Filtros**
   - Campos obligatorios:
     - "Naturaleza del Agua"
     - "Tipo de Derecho"

4. **Iniciar Proceso**
   - Clic en "Iniciar Procesamiento"
   - El progreso se mostrará en "Registro de Actividad"

5. **Limpiar**
   - Usar "Limpiar Campos" para resetear la interfaz