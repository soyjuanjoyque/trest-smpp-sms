Proyecto FastAPI SMPP

Requisitos

- Python 3.x
- MongoDB
- FastAPI
- Uvicorn
- pip (para manejar dependencias)

Instalación

1. Clonar el repositorio:
   git clone https://github.com/soyjuanjoyque/trest-smpp-sms.git

2. Crear y activar un entorno virtual:
   
   $ python -m venv venv
   $ source venv/bin/activate  # En Windows: $ venv\Scripts\activate

3. Instalar las dependencias:
   $ pip install -r requirements.txt

4. Configurar las variables de entorno en un archivo .env:

Cómo correr el proyecto

1. Asegurarse de que MongoDB esté corriendo localmente.
2. Iniciar la aplicación:
   
   $ uvicorn main:app --reload

Notas adicionales

- Para cambiar la configuración de SMPP, actualiza las variables en el archivo .env.
- La base de datos MongoDB debe estar corriendo en el puerto configurado en MONGO_URI.
