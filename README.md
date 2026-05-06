# Generador de Propuestas Comerciales — Periferia IT

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

Editar `.env` con las credenciales de MySQL:

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=solutions_db
DB_USER=root
DB_PASSWORD=tu_password
```

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

---

## Estructura del backend

```
backend/
├── main.py                          Entry point FastAPI
├── core/
│   ├── config.py                    Variables de entorno
│   ├── database.py                  SQLAlchemy engine + sesión
│   └── dependencies.py             get_db() para inyección
├── domain/                          Lógica de negocio pura
│   ├── catalogo/                    Entidades + servicio CRUD
│   ├── propuesta/                   Entidades + servicio generación PPTX
│   └── cronograma/                  Entidades + servicio generación XLSX
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
│   └── cronograma/                  POST /api/v1/cronograma/generar
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
| POST | `/api/v1/cronograma/generar` | Generar cronograma .xlsx (payload: `roles[{perfil,seniority,personas,torre}]`, `actividades[{torre,horas,personas}]`) |

Ver todos los endpoints en `http://localhost:8000/docs`.

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
