# Utiliser une image de base avec Python 3.11
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste des fichiers de l'application
COPY . .

# Exposer le port sur lequel l'application Flask écoute
EXPOSE 8000

# Commande pour exécuter l'application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
