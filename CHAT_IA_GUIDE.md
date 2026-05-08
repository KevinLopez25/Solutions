# Chat IA - Guía de Integración

## ✅ Completado

La integración de IA Groq está completa y funcional. El chat está disponible en todas las vistas de la aplicación.

## 🚀 Cómo empezar

### 1. Backend ya configurado
El archivo `.env` ya contiene tu clave Groq:
- **API Key**: `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`
- **Modelo**: `mixtral-8x7b-32768`
- **Endpoint**: `https://api.groq.com/openai/v1`

### 2. Iniciar servicios

**Backend (Python)**
```bash
cd backend
python server.py
# Ejecutará en http://localhost:8000
```

**Frontend (React)**
```bash
cd frontend
npm run dev
# Ejecutará en http://localhost:5173
```

## 💬 Funcionalidades del Chat

### Errors que detecta automáticamente:
- ✅ "desarrollador analista de requerimientos" → **Analista de Requerimientos**
- ✅ "desarrollador arquitecto" → **Arquitecto de Soluciones**
- ✅ "desarrollador scrum master" → **Scrum Master**
- ✅ Redacción confusa y nomenclatura inconsistente

### Cómo usar:
1. Abre la aplicación en `http://localhost:5173`
2. Busca el panel **"Asistente IA"** en la esquina inferior derecha
3. Pega tu texto de propuesta
4. Haz preguntas o pide correcciones
5. Presiona **Enter** para enviar (o **Shift+Enter** para nueva línea)

## 🔧 Estructura de archivos creados

```
backend/
├── .env                          # Configuración con API key
├── core/
│   ├── groq_client.py           # Cliente HTTP a Groq
│   └── config.py                # Config actualizada
├── domain/
│   └── ai/
│       ├── __init__.py
│       └── service.py           # Lógica de chat IA
└── api/v1/
    └── ai/
        ├── __init__.py
        └── router.py            # Endpoint POST /api/v1/ai/chat

frontend/
├── src/
│   ├── features/ai/
│   │   ├── components/
│   │   │   └── ChatBotPanel.jsx # Componente del chat
│   │   └── services/
│   │       └── aiService.js    # Llamadas a la API
│   └── App.jsx                 # Chat integrado globalmente
└── src/assets/styles/
    └── global.css              # Estilos del chat
```

## 📡 API Endpoint

**POST** `/api/v1/ai/chat`

**Request:**
```json
{
  "messages": [
    { "role": "user", "content": "Revisa este texto: desarrollador analista..." }
  ]
}
```

**Response:**
```json
{
  "reply": "El término 'desarrollador analista de requerimientos' es redundante..."
}
```

## 🎨 Diseño

- Chat ubicado en **esquina inferior derecha**
- Tema oscuro con acentos verdes (coherente con el diseño)
- Auto-scroll al recibir mensajes
- Indicador de escritura
- Botón para cerrar/abrir
- Disponible en **todas las vistas**

## 🔄 Mejoras implementadas

✅ Mejor manejo de errores de conexión  
✅ Auto-scroll en el chat  
✅ Indicador de escritura  
✅ Placeholder mejorado con instrucción (Shift+Enter)  
✅ Emojis para mejor UX  
✅ Prompt especializado en corrección de propuestas  
✅ Temperatura optimizada (0.3) para respuestas consistentes  
✅ Tokens aumentados a 1024 para respuestas más detalladas  

## ⚙️ Configuración personalizable

Edita `backend/core/config.py` si quieres cambiar:
- **GROQ_MODEL**: Cambia el modelo Groq
- **GROQ_BASE_URL**: URL del endpoint
- **Temperature/max_tokens**: En `groq_client.py`

## 🆘 Troubleshooting

**El chat no conecta**
- Verifica que el backend esté corriendo en `http://localhost:8000`
- Comprueba que la clave API en `.env` sea válida
- Revisa la consola del navegador (F12 → Console)

**Respuestas lentas**
- Groq puede tardar 2-5 segundos
- El modelo `mixtral-8x7b-32768` es poderoso pero más lento que otros

**Error de CORS**
- Asegúrate que `ALLOWED_ORIGINS` en `.env` incluya `http://localhost:5173`

---

**Listo para usar** 🚀 El chat IA está integrado, funcional y optimizado para mejorar propuestas comerciales.
