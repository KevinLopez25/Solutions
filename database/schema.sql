-- =============================================================================
-- Schema: solutions_db
-- Reemplaza el archivo Generales_para_todos.xlsx
-- Tablas: torres, perfiles, consideraciones, entregables, fuera_del_alcance
-- =============================================================================

CREATE DATABASE IF NOT EXISTS solutions_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE solutions_db;

-- ---------------------------------------------------------------------------
-- Tabla maestra de torres (catálogo de especialidades)
-- ---------------------------------------------------------------------------
CREATE TABLE torres (
  id         INT UNSIGNED   NOT NULL AUTO_INCREMENT,
  nombre     VARCHAR(120)   NOT NULL COMMENT 'Nombre legible, ej: "Backend", "QA Automation"',
  nombre_norm VARCHAR(120)  NOT NULL COMMENT 'Nombre normalizado (mayúsculas, sin tildes)',
  activa     TINYINT(1)     NOT NULL DEFAULT 1,
  creado_en  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_torres_nombre_norm (nombre_norm)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Catálogo maestro de torres / especialidades técnicas';


-- ---------------------------------------------------------------------------
-- Perfiles por torre  (hoja "Perfiles" del Excel)
-- ---------------------------------------------------------------------------
CREATE TABLE perfiles (
  id          INT UNSIGNED   NOT NULL AUTO_INCREMENT,
  torre_id    INT UNSIGNED   NOT NULL,
  rol         VARCHAR(200)   NOT NULL COMMENT 'Nombre del rol, ej: "Tech Lead Backend"',
  descripcion TEXT           NOT NULL COMMENT 'Descripción completa del perfil',
  activo      TINYINT(1)     NOT NULL DEFAULT 1,
  creado_en   DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY fk_perfiles_torre (torre_id),
  CONSTRAINT fk_perfiles_torre
    FOREIGN KEY (torre_id) REFERENCES torres (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Perfiles de roles agrupados por torre';


-- ---------------------------------------------------------------------------
-- Consideraciones por torre  (hoja "Consideraciones" del Excel)
-- ---------------------------------------------------------------------------
CREATE TABLE consideraciones (
  id          INT UNSIGNED   NOT NULL AUTO_INCREMENT,
  torre_id    INT UNSIGNED       NULL COMMENT 'NULL = aplica a todas las torres (GENERALES)',
  texto       TEXT           NOT NULL,
  es_general  TINYINT(1)     NOT NULL DEFAULT 0 COMMENT '1 cuando aplica a todas las torres',
  activa      TINYINT(1)     NOT NULL DEFAULT 1,
  orden       SMALLINT       NOT NULL DEFAULT 0 COMMENT 'Orden de aparición en la diapositiva',
  creado_en   DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY fk_consideraciones_torre (torre_id),
  CONSTRAINT fk_consideraciones_torre
    FOREIGN KEY (torre_id) REFERENCES torres (id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Consideraciones genéricas por torre (pill Consideraciones)';


-- ---------------------------------------------------------------------------
-- Entregables por torre  (hoja "Entregables" del Excel)
-- ---------------------------------------------------------------------------
CREATE TABLE entregables (
  id          INT UNSIGNED   NOT NULL AUTO_INCREMENT,
  torre_id    INT UNSIGNED   NOT NULL,
  item        VARCHAR(500)   NOT NULL COMMENT 'Texto del ítem entregable',
  activo      TINYINT(1)     NOT NULL DEFAULT 1,
  orden       SMALLINT       NOT NULL DEFAULT 0,
  creado_en   DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY fk_entregables_torre (torre_id),
  CONSTRAINT fk_entregables_torre
    FOREIGN KEY (torre_id) REFERENCES torres (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Entregables del catálogo por torre (pill Entregables)';


-- ---------------------------------------------------------------------------
-- Fuera del Alcance por torre  (hoja "Fuera del Alcance" del Excel)
-- ---------------------------------------------------------------------------
CREATE TABLE fuera_del_alcance (
  id          INT UNSIGNED   NOT NULL AUTO_INCREMENT,
  torre_id    INT UNSIGNED   NOT NULL,
  item        VARCHAR(600)   NOT NULL COMMENT 'Cláusula fuera del alcance',
  activo      TINYINT(1)     NOT NULL DEFAULT 1,
  orden       SMALLINT       NOT NULL DEFAULT 0,
  creado_en   DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY fk_fda_torre (torre_id),
  CONSTRAINT fk_fda_torre
    FOREIGN KEY (torre_id) REFERENCES torres (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Ítems fuera del alcance por torre (pill FDA)';


-- =============================================================================
-- Datos semilla: torres comunes (ajustar según catálogo real del Excel)
-- =============================================================================
INSERT INTO torres (nombre, nombre_norm) VALUES
  ('Backend',              'BACKEND'),
  ('Frontend',             'FRONTEND'),
  ('QA Automation',        'QA AUTOMATION'),
  ('QA Manual',            'QA MANUAL'),
  ('DevOps',               'DEVOPS'),
  ('Data & Analytics',     'DATA & ANALYTICS'),
  ('Arquitectura',         'ARQUITECTURA'),
  ('Mobile',               'MOBILE'),
  ('Integraciones',        'INTEGRACIONES'),
  ('Seguridad',            'SEGURIDAD'),
  ('BI',                   'BI'),
  ('Cloud',                'CLOUD'),
  ('Gestión de Proyectos', 'GESTION DE PROYECTOS');


-- =============================================================================
-- Vistas útiles
-- =============================================================================

CREATE OR REPLACE VIEW v_perfiles AS
  SELECT p.id, t.nombre AS torre, t.nombre_norm AS torre_norm,
         p.rol, p.descripcion, p.activo
  FROM perfiles p
  JOIN torres t ON t.id = p.torre_id;

CREATE OR REPLACE VIEW v_entregables AS
  SELECT e.id, t.nombre AS torre, t.nombre_norm AS torre_norm,
         e.item, e.orden, e.activo
  FROM entregables e
  JOIN torres t ON t.id = e.torre_id
  ORDER BY t.nombre, e.orden;

CREATE OR REPLACE VIEW v_consideraciones AS
  SELECT c.id,
         COALESCE(t.nombre, 'GENERALES') AS torre,
         COALESCE(t.nombre_norm, 'GENERALES') AS torre_norm,
         c.texto, c.es_general, c.orden, c.activa
  FROM consideraciones c
  LEFT JOIN torres t ON t.id = c.torre_id
  ORDER BY COALESCE(t.nombre, 'GENERALES'), c.orden;

CREATE OR REPLACE VIEW v_fuera_del_alcance AS
  SELECT f.id, t.nombre AS torre, t.nombre_norm AS torre_norm,
         f.item, f.orden, f.activo
  FROM fuera_del_alcance f
  JOIN torres t ON t.id = f.torre_id
  ORDER BY t.nombre, f.orden;
