-- =============================================================================
--  AUDITOR_C# — Esquema de base de datos (PostgreSQL 16+)
--  Corresponde al Modelo Entidad-Relación del Capítulo V.
--
--  Uso:  psql "<cadena de conexión>" -f esquema_postgresql.sql
--  (El servidor también crea estas tablas por sí solo si no existen, a partir
--   de backend/persistencia/modelos.py; este script es el equivalente en SQL.)
--  Es idempotente: si se ejecuta de nuevo solo crea lo que falte, sin borrar datos.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- USUARIO: personas que usan la herramienta y su rol.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuario (
    id_usuario       SERIAL        NOT NULL,
    nombre_usuario   VARCHAR(120)  NOT NULL,
    correo           VARCHAR(160)  NOT NULL,
    contrasena_hash  VARCHAR(255)  NOT NULL,   -- scrypt$<sal>$<hash>, nunca texto plano
    rol              VARCHAR(20)   NOT NULL,
    activo           BOOLEAN       NOT NULL DEFAULT TRUE,
    fecha_creacion   TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT usuario_pkey       PRIMARY KEY (id_usuario),
    CONSTRAINT usuario_correo_key UNIQUE (correo),
    CONSTRAINT ck_usuario_rol     CHECK (rol IN ('Administrador', 'Desarrollador', 'Auditor'))
);

-- -----------------------------------------------------------------------------
-- PROYECTO: solución C# registrada por un usuario (el nombre de la carpeta analizada).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS proyecto (
    id_proyecto      SERIAL        NOT NULL,
    nombre           VARCHAR(200)  NOT NULL,
    id_usuario       INTEGER       NOT NULL,
    fecha_creacion   TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT proyecto_pkey              PRIMARY KEY (id_proyecto),
    CONSTRAINT uq_proyecto_nombre_usuario UNIQUE (nombre, id_usuario),
    CONSTRAINT proyecto_id_usuario_fkey   FOREIGN KEY (id_usuario) REFERENCES usuario (id_usuario)
);

-- -----------------------------------------------------------------------------
-- REGLA: catálogo de reglas heurísticas del motor (cuatro módulos).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS regla (
    codigo_regla     VARCHAR(20)   NOT NULL,
    descripcion      VARCHAR(200)  NOT NULL,
    modulo           VARCHAR(80)   NOT NULL,
    categoria        VARCHAR(80)   NOT NULL,
    severidad        VARCHAR(20)   NOT NULL,
    activa           BOOLEAN       NOT NULL DEFAULT TRUE,
    CONSTRAINT regla_pkey         PRIMARY KEY (codigo_regla),
    CONSTRAINT ck_regla_severidad CHECK (severidad IN ('CRÍTICO', 'ADVERTENCIA', 'BAJO'))
);

-- -----------------------------------------------------------------------------
-- REPORTE: resultado de un análisis. Solo guarda ids (no datos personales).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reporte (
    id_reporte           SERIAL            NOT NULL,
    codigo_reporte       UUID              NOT NULL,   -- id público del informe .json
    id_usuario           INTEGER           NOT NULL,
    id_proyecto          INTEGER           NOT NULL,
    fecha_hora           TIMESTAMPTZ       NOT NULL DEFAULT now(),
    loc_total            INTEGER           NOT NULL,
    vulnerabilidades     INTEGER           NOT NULL,
    densidad_errores     DOUBLE PRECISION  NOT NULL,   -- hallazgos por cada 100 LOC
    score_gobierno       SMALLINT          NOT NULL,
    cumplimiento_modulo  JSONB             NOT NULL,   -- {"Módulo 1: Seguridad": 76, ...}
    archivo_json         VARCHAR(500),
    CONSTRAINT reporte_pkey                PRIMARY KEY (id_reporte),
    CONSTRAINT reporte_codigo_reporte_key  UNIQUE (codigo_reporte),
    CONSTRAINT reporte_id_usuario_fkey     FOREIGN KEY (id_usuario)  REFERENCES usuario (id_usuario),
    CONSTRAINT reporte_id_proyecto_fkey    FOREIGN KEY (id_proyecto) REFERENCES proyecto (id_proyecto),
    CONSTRAINT ck_reporte_score            CHECK (score_gobierno BETWEEN 0 AND 100),
    CONSTRAINT ck_reporte_conteos          CHECK (loc_total >= 0 AND vulnerabilidades >= 0)
);

-- -----------------------------------------------------------------------------
-- HALLAZGO: cada problema detectado dentro de un reporte.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hallazgo (
    id_hallazgo      SERIAL        NOT NULL,
    id_reporte       INTEGER       NOT NULL,
    codigo_regla     VARCHAR(20)   NOT NULL,
    severidad        VARCHAR(20)   NOT NULL,
    archivo          VARCHAR(500)  NOT NULL,
    linea            INTEGER       NOT NULL,
    descripcion      TEXT          NOT NULL,
    recomendacion    TEXT          NOT NULL,
    estado           VARCHAR(20)   NOT NULL DEFAULT 'Pendiente',
    CONSTRAINT hallazgo_pkey              PRIMARY KEY (id_hallazgo),
    CONSTRAINT hallazgo_id_reporte_fkey   FOREIGN KEY (id_reporte)   REFERENCES reporte (id_reporte) ON DELETE CASCADE,
    CONSTRAINT hallazgo_codigo_regla_fkey FOREIGN KEY (codigo_regla) REFERENCES regla (codigo_regla),
    CONSTRAINT ck_hallazgo_severidad      CHECK (severidad IN ('CRÍTICO', 'ADVERTENCIA', 'BAJO')),
    CONSTRAINT ck_hallazgo_estado         CHECK (estado IN ('Pendiente', 'Solucionado', 'Fallido')),
    CONSTRAINT ck_hallazgo_linea          CHECK (linea > 0)
);

-- -----------------------------------------------------------------------------
-- REPORTE_REGLA: entidad asociativa REPORTE N:M REGLA ("aplica").
--   Una fila por cada regla ejecutada en el análisis (todas por defecto).
--   evaluada = criterio elegido por el auditor al revisar el reporte.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reporte_regla (
    id_reporte       INTEGER       NOT NULL,
    codigo_regla     VARCHAR(20)   NOT NULL,
    evaluada         BOOLEAN       NOT NULL DEFAULT TRUE,
    CONSTRAINT reporte_regla_pkey              PRIMARY KEY (id_reporte, codigo_regla),
    CONSTRAINT reporte_regla_id_reporte_fkey   FOREIGN KEY (id_reporte)   REFERENCES reporte (id_reporte) ON DELETE CASCADE,
    CONSTRAINT reporte_regla_codigo_regla_fkey FOREIGN KEY (codigo_regla) REFERENCES regla (codigo_regla)
);

-- Índices para las consultas más frecuentes (historial y detalle de reportes).
CREATE INDEX IF NOT EXISTS ix_reporte_id_usuario      ON reporte  (id_usuario);
CREATE INDEX IF NOT EXISTS ix_reporte_id_proyecto     ON reporte  (id_proyecto);
CREATE INDEX IF NOT EXISTS ix_hallazgo_id_reporte     ON hallazgo (id_reporte);
CREATE INDEX IF NOT EXISTS ix_hallazgo_codigo_regla   ON hallazgo (codigo_regla);

-- -----------------------------------------------------------------------------
-- Datos iniciales: catálogo de reglas implementadas en el motor.
-- (El Administrador inicial lo crea el servidor al arrancar, con la contraseña
--  ya cifrada; no se escribe aquí para no dejar contraseñas en el script.)
-- -----------------------------------------------------------------------------
INSERT INTO regla (codigo_regla, descripcion, modulo, categoria, severidad, activa) VALUES
    ('SEG-001',  'Hardcoded Credentials (CWE-259)',                        'Módulo 1: Seguridad',   'Seguridad (OWASP)',    'CRÍTICO',     TRUE),
    ('SEG-002',  'Inyección SQL - Consultas directas sin parametrizar',    'Módulo 1: Seguridad',   'Seguridad (OWASP)',    'CRÍTICO',     TRUE),
    ('PERF-001', 'Variables locales declaradas sin utilización en bloque', 'Módulo 2: Rendimiento', 'Rendimiento (.NET)',   'ADVERTENCIA', TRUE),
    ('MEM-004',  'Clases IDisposable sin bloque ''using'' o cierre formal', 'Módulo 3: Memoria',     'Gestión de Memoria',   'ADVERTENCIA', TRUE),
    ('GOV-001',  'Falta de nomenclatura estándar CamelCase / PascalCase',  'Módulo 4: Gobierno',    'Gobierno Estructural', 'BAJO',        TRUE)
ON CONFLICT (codigo_regla) DO NOTHING;

COMMIT;
