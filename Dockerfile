# Dockerfile for BAGHEWALA-X
# Multi‑stage build: backend (FastAPI) and frontend (React/Vite)

# ---------- Backend ----------
FROM python:3.11-slim AS backend
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY backend/app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---------- Frontend ----------
FROM node:20-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json ./
COPY frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

# ---------- Final image ----------
FROM python:3.11-slim
WORKDIR /app
COPY --from=backend /app /app
COPY --from=frontend /frontend/dist ./frontend/dist
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
