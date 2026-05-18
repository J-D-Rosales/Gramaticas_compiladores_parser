# Usamos una imagen ligera de Python
FROM python:3.10-slim

# Evitamos que Python escriba archivos .pyc y forzamos el output en consola
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalamos Graphviz a nivel del sistema operativo (Requisito para st.graphviz_chart)
RUN apt-get update && apt-get install -y \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# Establecemos el directorio de trabajo
WORKDIR /app

# Copiamos las dependencias primero para aprovechar el caché de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código del proyecto
COPY . .

# Exponemos el puerto estándar de Streamlit
EXPOSE 8501

# Comando para ejecutar la app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]