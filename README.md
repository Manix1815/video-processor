# TikTok Video Processor

Batch video processor usando FFmpeg, deployable en Railway.

> ⚠️ **Uso responsable**: Solo procesa videos para los que tengas permiso explícito del creador original.

## Qué hace

Aplica automáticamente estas transformaciones a cada video:
- Reescala a formato vertical 9:16 (1080x1920)
- Espejo horizontal
- Ajuste de color (brillo, saturación, contraste)
- Velocidad ligeramente alterada (±5%)
- Recodificación completa H.264/AAC

Los valores se **aleatorizan** en cada video para que cada output sea único.

## Deploy en Railway

### 1. Sube el código a GitHub
```bash
git init
git add .
git commit -m "Initial commit"
gh repo create tiktok-processor --public --push
```

### 2. Crea proyecto en Railway
1. Ve a [railway.com](https://railway.com)
2. New Project → Deploy from GitHub repo
3. Selecciona tu repositorio
4. Railway detectará el Dockerfile automáticamente

### 3. Variables de entorno (opcionales)
En Railway → Variables:
```
INPUT_DIR=/app/input
OUTPUT_DIR=/app/output
PORT=8080
```

## Uso de la API

### Ver estado
```bash
GET https://tu-app.railway.app/
```

### Lanzar procesamiento batch
```bash
POST https://tu-app.railway.app/process
```

### Ver progreso
```bash
GET https://tu-app.railway.app/status
```

## Uso local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Procesar una carpeta entera
python3 process.py --input ./mis_videos --output ./procesados

# Procesar un solo archivo
python3 process.py --file video.mp4 --output ./procesados
```

## Estructura del proyecto
```
tiktok-processor/
├── process.py       # Lógica FFmpeg
├── app.py           # API HTTP (Flask)
├── Dockerfile       # Para Railway
├── railway.toml     # Config Railway
└── requirements.txt
```

## Notas sobre Railway

- El plan **Hobby** (~$5/mes) es suficiente para uso moderado
- Los archivos en `/app/input` y `/app/output` **no persisten** entre deploys
- Para almacenamiento persistente, conecta un **Railway Volume** o usa un bucket S3/R2
