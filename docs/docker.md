# Docker Deployment Guide

Unsere Docker Container laufen auf dem KIT Server der Fakultät Informatik. Dort ist unter /var1/study/
die compose.yaml hinterlegt. Um das Widget auf einem anderen Server laufen zu lassen, wird in der folgenden
Anleitung erklärt, wie man die einzelnen Images baut, tagt und pusht.

**WICHTIG: Alle Container sind auf einem privaten DockerHub gespusht. Die Pfade zum pushen müssen 
demnach auf den eigenen User in DockerHub geändert werden!**

## Abhängigkeiten

- Docker Destop
- Docker-Account
- Projekt lokal geklont:
    - HTTPS: https://git.informatik.fh-nuernberg.de/muellerlu93279/kiwi-ki-chatbot-widget.git
    - SSH: git@git.informatik.fh-nuernberg.de:muellerlu93279/kiwi-ki-chatbot-widget.git

    
## 1. Base Image erstellen und deployen
Das Base Image baut die Basis für unser Widget. Um die push und build Zeiten zu reduzieren haben wir im Laufe der 
Zeit dieses Base Image eingeführt. Im Base Image befinden sich alle Dependencies für Playwright(Browser) und die 
Bibliotheken aus den requirements.

### Base Image Dockerfile

```dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV DISPLAY=:99

COPY requirements/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

RUN playwright install --with-deps chromium
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libgdk-pixbuf-2.0-0 \
    libgtk-3-0 \
    libatk-bridge2.0-0 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcups2 \
    libxfixes3 \
    libexpat1 \
    libatk1.0-0 \
    libdbus-1-3 \
    libxext6 \
    libxi6 \
    libxtst6 \
    libxrender1 \
    libxcursor1 \
    libxss1 \
    libxt6 \
    libxinerama1 \
    fonts-liberation \
    libappindicator3-1 \
    lsb-release \
    xdg-utils \
    wget
```

### Base Image bauen und pushen

```bash
# 1. Base Image bauen, man muss sich dafür im Root befinden vom Projekt
docker build -t kiwi-base:latest -f Dockerfile.base .

# 2. Image für Docker Hub taggen (ersetze 'dein-username' mit deinem Docker Hub Username)
docker tag kiwi-base:latest dein-username/kiwi-base:latest

# 3. Bei Docker Hub anmelden (falls noch nicht geschehen)
docker login

# 4. Image zu Docker Hub pushen
docker push dein-username/kiwi-base:latest
```

## 2. Service Container erstellen

### Beispiel Widget Dockerfile

```dockerfile
FROM dein-username/kiwi-base:latest AS base

WORKDIR /widget

COPY ./src/widget ./src/widget
COPY ./src/settings.py ./src/settings.py
COPY ./src/.env ./src/.env 
COPY ./src/clients ./src/clients 

CMD ["uvicorn", "src.widget.frontend.app:app", "--host", "0.0.0.0", "--port", "9090", "--proxy-headers"]
```

### Service Container bauen und pushen

Neben dem Base Image braucht man auch die eigentlichen Services:

```bash
# 1. Service Image bauen
docker build -t widget-service:latest -f Dockerfile.widget .

# 2. Image für Docker Hub taggen
docker tag widget-service:latest dein-username/widget-service:latest

# 3. Image zu Docker Hub pushen
docker push dein-username/widget-service:latest
```

Die anderen Services lassen sich mit dem selben Verfahren bauen. Lediglich die Dockerfile Datei muss
angepasst werden und es müssen andere Namen vergeben werden. Folgende weitere Namen haben wir immer vergebene
damit man unsere compose.yaml zum großen Teil wiederverwenden kann:

- Dockerfile.admin -> admin-service
- Dockerfile.dense -> dense-service
- Dockerfile.ingest -> ingest-service
- Dockerfile.sparse -> sparse-service


## 3. Docker Compose anpassen

Die compose.yaml muss auch leicht angepasst werden:

```yaml
# Alt:
services:
  widget:
    image: lksmler/widget-service:latest
    
# Neu:
services:
  widget:
    image: DEIN-USERNAME/widget-service:latest
```

## 4. Server

Auf dem Server auf dem man die Docker Container laufen lassen möchte, muss man lediglich eine compose.yaml erstellen und
diese dann mit folgenden Befehlen starten:

```bash
docker compose -f compose.yaml pull

docker compose -f compose.yaml up -d # -d ist der detached Modus, so laufen die Contaienr auch weiter wenn man sich abmeldet
```
Das widget sollte dann unter http://adresse-des-servers:9090 verfügbar sein und das admin-panel unter Port 9000.

Falls man den Destop Screenshot benutzen möchte muss man auf dem Server noch eine https Verbindung bauen.

Die compose.yaml ist wegen der Keys die dort hinterlegt sind nur auf dem KIT-Server zu finden. Falls Ihr die braucht und
keinen Zugang habt, könnt ihr Yilmaz Duman kontaktieren.




