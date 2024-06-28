# Dockerfile para Dron
FROM python:3.9

WORKDIR /app

COPY Dron/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/clave && chmod 777 /app/clave

COPY Nucleo/certificate.crt /app
COPY Dron/AD_Dron.py /app
COPY Nucleo/Mapa.py /app
COPY Nucleo/claveCifrada.json /app/clave/

CMD ["python", "AD_Dron.py"]
