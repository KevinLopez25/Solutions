# Generador de Propuestas Comerciales 

Genera presentaciones PowerPoint (.pptx) de propuestas comerciales y cronogramas (.xlsx) a partir del Excel de estimación del proyecto.

## Arquitectura

```
Solutions/
├── backend/          FastAPI (Python 3.10+)
├── frontend/         React + Vite
└── database/         Schema MySQL
```

**Flujo general:**
```
Frontend (React)
  └─ Sube Excel → selecciona torres/filial/pills
  └─ POST /api/v1/propuesta/generar
       └─ Consulta BD → build_catalog_data()
       └─ Generadores PPTX en cadena
       └─ Retorna .pptx en base64 → descarga automática
```

---

## Requisitos previos

- Python 3.10+
- Node.js 18+
- MySQL 8.0+

---

## 1. Base de datos

Ejecutar los dos scripts en orden en MySQL Workbench:

```sql
-- 1. Crea las tablas
SOURCE database/schema.sql;

-- 2. Carga todos los datos del catálogo
SOURCE database/seed_data.sql;
```

**¿Qué queda cargado después de ejecutar ambos scripts?**

| Tabla | Registros |
|---|---|
| `torres` | 14 torres (Fullstack, QA, Arquitectura, Datos, RPA, DevOps, Ciberseguridad, IA, SAP, PMO, Mobile, Portales, Integración, Soporte) |
| `perfiles` | 90 perfiles con rol y descripción por torre |
| `fuera_del_alcance` | 158 ítems por torre |
| `consideraciones` | 52 consideraciones por torre y generales |
| `entregables` | 64 entregables por torre |

> Todos los datos provienen del archivo `Generales_para_todos.xlsx` que se usaba antes. La BD queda lista para usar desde el primer arranque.

---

## 2. Backend

```bash
cd backend
copy .env.example .env
```

Editar `.env` con las credenciales de MySQL y la API key de Groq:

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=solutions_db
DB_USER=root
DB_PASSWORD=tu_password

GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
```

> La `GROQ_API_KEY` es necesaria para el agente conversacional (chatbot Peri). Se obtiene en [console.groq.com](https://console.groq.com) → API Keys → Create API Key. Sin esta key el chatbot no funciona pero el resto de la app sí.

Instalar dependencias e iniciar:

```bash
pip install -r requirements.txt
python server.py
```

La API queda disponible en `http://localhost:8000`.  
Documentación interactiva: `http://localhost:8000/docs`

---

## 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

La app queda disponible en `http://localhost:5173`.

### Diseño visual

Fuentes **Syne** (títulos) + **Figtree** (cuerpo), paleta verde oscuro (`#00E676` / `#040906`), animación de fondo con orbs y partículas, robots decorativos CSS 3D en las esquinas.

### Flujo del wizard (6 pasos)

| Paso | Pantalla |
|---|---|
| 0 | **Modo** — elige Propuesta PPT o Cronograma |
| 1 | **Excel** — sube el archivo de estimación |
| 2 | **Torres / Perfiles** — revisa datos del Excel o selecciona torres manualmente + modo de perfiles (Catálogo completo / Elegir perfiles) |
| 3 | **Filial** — corp / group / cbit |
| 4 | **Secciones** — pills para activar genéricos |
| 5 | **Resumen** — confirma y genera el documento |

### Componentes nuevos

| Archivo | Descripción |
|---|---|
| `src/components/BgCanvas.jsx` | Canvas animado: orbs, partículas y grilla verde |
| `src/components/Bot3D.jsx` | Robot 3D en esquina inferior derecha — clic abre/cierra el chatbot |
| `src/components/AgentChat.jsx` | Panel de chat flotante con el agente Peri |
| `src/features/chat/services/chatService.js` | Llamadas a los endpoints del agente IA |

---

## Estructura del backend

```
backend/
├── main.py                          Entry point FastAPI
├── core/
│   ├── config.py                    Variables de entorno (incluye GROQ_API_KEY)
│   ├── database.py                  SQLAlchemy engine + sesión
│   ├── dependencies.py              get_db() para inyección
│   └── groq_client.py               Cliente singleton de Groq
├── domain/                          Lógica de negocio pura
│   ├── catalogo/                    Entidades + servicio CRUD
│   ├── propuesta/                   Entidades + servicio generación PPTX
│   ├── cronograma/                  Entidades + servicio generación XLSX
│   └── ia/
│       ├── entities.py              Modelos Pydantic: chat, validación de perfiles
│       └── service.py               Lógica del agente (fases, Groq, config builder)
├── infrastructure/
│   ├── models/catalogo.py           Modelos SQLAlchemy (ORM)
│   ├── repositories/
│   │   └── catalogo_repository.py  Acceso a BD + build_catalog_data()
│   └── generators/
│       ├── __init__.py              Orquestador (llama los 3 generators)
│       ├── fda_perfiles.py          Slides Perfiles y Fuera del Alcance
│       ├── consideraciones.py       Slide Consideraciones
│       ├── cronograma_entregables.py Slide Entregables
│       └── cronograma_excel.py      Generación del cronograma .xlsx
├── api/v1/
│   ├── catalogo/                    CRUD: /api/v1/catalogo/*
│   ├── propuesta/                   POST /api/v1/propuesta/generar
│   ├── cronograma/                  POST /api/v1/cronograma/generar
│   └── ia/                          Endpoints del agente IA
└── templates/                       Plantillas .pptx (una por filial)
```

---

## Endpoints principales

| Método | URL | Descripción |
|---|---|---|
| GET | `/api/v1/catalogo/torres` | Listar torres |
| POST | `/api/v1/catalogo/perfiles` | Crear perfil |
| GET | `/api/v1/catalogo/perfiles?torre_id=1` | Perfiles de una torre |
| POST | `/api/v1/propuesta/generar` | Generar propuesta .pptx |
| POST | `/api/v1/cronograma/generar` | Generar cronograma .xlsx |
| POST | `/api/v1/ia/chat` | Turno de conversación con el agente Peri |
| POST | `/api/v1/ia/validar-perfiles` | Clasifica nombres de perfiles con Groq |
| POST | `/api/v1/ia/confirmar-perfil` | Confirma o descarta una corrección de perfil |

Ver todos los endpoints en `http://localhost:8000/docs`.

---

## Agente conversacional (Peri)

El robot 3D en la esquina inferior derecha abre un chat donde el agente **Peri** guía al usuario en 5 fases para recopilar los datos necesarios y generar la propuesta PPT:

| Fase | Datos que recoge |
|---|---|
| 1 | Nombre del cliente y proyecto |
| 2 | Torres tecnológicas del proyecto |
| 3 | Perfiles del equipo y cantidad de personas |
| 4 | Filial (corp / group / cbit) |
| 5 | Confirmación y generación |

**Modelo:** `llama-3.3-70b-versatile` (chat) vía Groq.

El agente acumula contexto turno a turno y al finalizar construye automáticamente el payload de `/api/v1/propuesta/generar`, mostrando un botón para descargar la PPT directamente desde el chat.

---

## Cómo funciona la generación de propuesta

El frontend parsea el Excel del cliente en tres hojas:

- **RESUMEN** → proyecto, cliente, torres con horas
- **Estimación** → consideraciones (col J), fuera del alcance (col K), entregables (col M)
- **Anexos** → perfiles del equipo

Con esos datos construye un payload que envía al backend (`POST /api/v1/propuesta/generar`). El backend consulta la BD para obtener los datos del catálogo y llama a los tres generadores en cadena sobre la plantilla PPTX de la filial elegida.

### Pills

Cada sección tiene una pill que controla si se mezclan datos del catálogo (BD) con los del Excel del cliente:

| Pill | ON | OFF |
|---|---|---|
| Perfiles | Excel + catálogo BD para complementar | Solo Excel (o catálogo completo si Excel vacío) |
| Fuera del Alcance | Cláusula general | Ítems por torre del Excel o catálogo |
| Consideraciones | Excel + catálogo BD filtrado por torre | Solo Excel |
| Entregables | Excel + catálogo BD para torres sin datos | Solo Excel (o catálogo si Excel vacío) |

---

## Generadores PPTX

### `fda_perfiles.py` — Perfiles y Fuera del Alcance
Pagina perfiles en slides de máximo 4 tarjetas. Centra automáticamente 1–3 perfiles. Para FDA, si hay más de 1 torre muestra la cláusula general; si hay 1 torre muestra sus ítems específicos (máx 6 por slide).

### `consideraciones.py` — Consideraciones
Incluye siempre los ítems del Excel. Con pill ON agrega genéricos de la BD filtrados por torre. Los textos largos expanden el grupo automáticamente. Reemplaza el nombre del cliente y la filial en el texto.

### `cronograma_entregables.py` — Entregables
Soporta 1–4 torres por slide (layout adaptativo). Si hay más de 4 torres duplica el slide. Con pill ON complementa con el catálogo de la BD para torres sin datos del Excel.

---

## Modelo de datos

```
torres (1) ──< perfiles
torres (1) ──< consideraciones   (NULL = aplica a todas)
torres (1) ──< entregables
torres (1) ──< fuera_del_alcance
```
