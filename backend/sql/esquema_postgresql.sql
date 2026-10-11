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
-- REGLA: catálogo de reglas. La lógica no está en el código: tipo_deteccion
-- elige un detector genérico del motor y patrones/parametros le dicen qué
-- buscar. El Administrador los edita (o crea reglas nuevas) desde la interfaz.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS regla (
    codigo_regla         VARCHAR(20)   NOT NULL,
    descripcion          VARCHAR(200)  NOT NULL,
    modulo               VARCHAR(80)   NOT NULL,
    categoria            VARCHAR(80)   NOT NULL,
    severidad            VARCHAR(20)   NOT NULL,
    activa               BOOLEAN       NOT NULL DEFAULT TRUE,
    tipo_deteccion       VARCHAR(40),
    patrones             JSONB         NOT NULL DEFAULT '[]',   -- p. ej. ["'", "--", ";"]
    parametros           JSONB         NOT NULL DEFAULT '{}',
    owasp_2021           VARCHAR(10),                           -- p. ej. A03:2021
    owasp_2025           VARCHAR(10),                           -- p. ej. A05:2025
    cwe                  VARCHAR(20),
    mensaje              TEXT,                                  -- admite el marcador {detalle}
    recomendacion        TEXT,
    predefinida          BOOLEAN       NOT NULL DEFAULT FALSE,
    fecha_actualizacion  TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT regla_pkey         PRIMARY KEY (codigo_regla),
    CONSTRAINT ck_regla_severidad CHECK (severidad IN ('CRÍTICO', 'ADVERTENCIA', 'BAJO'))
);

-- Migración desde la primera versión del esquema (tabla regla con 6 columnas).
ALTER TABLE regla ADD COLUMN IF NOT EXISTS tipo_deteccion      VARCHAR(40);
ALTER TABLE regla ADD COLUMN IF NOT EXISTS patrones            JSONB       NOT NULL DEFAULT '[]';
ALTER TABLE regla ADD COLUMN IF NOT EXISTS parametros          JSONB       NOT NULL DEFAULT '{}';
ALTER TABLE regla ADD COLUMN IF NOT EXISTS owasp_2021          VARCHAR(10);
ALTER TABLE regla ADD COLUMN IF NOT EXISTS owasp_2025          VARCHAR(10);
ALTER TABLE regla ADD COLUMN IF NOT EXISTS cwe                 VARCHAR(20);
ALTER TABLE regla ADD COLUMN IF NOT EXISTS mensaje             TEXT;
ALTER TABLE regla ADD COLUMN IF NOT EXISTS recomendacion       TEXT;
ALTER TABLE regla ADD COLUMN IF NOT EXISTS predefinida         BOOLEAN     NOT NULL DEFAULT FALSE;
ALTER TABLE regla ADD COLUMN IF NOT EXISTS fecha_actualizacion TIMESTAMPTZ NOT NULL DEFAULT now();

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
-- Datos iniciales: catálogo de reglas de fábrica (OWASP Top 10:2021 y 2025).
-- Las reglas que el Administrador ya editó NO se sobrescriben: solo se
-- completan las que vienen de la primera versión (tipo_deteccion vacío).
-- (El Administrador inicial lo crea el servidor al arrancar, con la contraseña
--  ya cifrada; no se escribe aquí para no dejar contraseñas en el script.)
-- -----------------------------------------------------------------------------
INSERT INTO regla (codigo_regla, descripcion, modulo, categoria, severidad, activa, tipo_deteccion, patrones,
                   parametros, owasp_2021, owasp_2025, cwe, mensaje, recomendacion, predefinida) VALUES
    ('SEG-001', 'Credenciales embebidas en el código', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'CRÍTICO', TRUE, 'literal_asignado', '["password", "pwd", "contrasena", "clave", "secret", "apikey", "api_key", "token", "connectionstring"]'::jsonb, '{}'::jsonb, 'A07:2021', 'A07:2025', 'CWE-798', '{detalle} Almacenar secretos en el código vulnera CWE-798.', 'Mover la credencial a variables de entorno, User Secrets o un almacén de secretos (Azure Key Vault).', TRUE),
    ('SEG-002', 'Inyección SQL: consulta sin parametrizar', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'CRÍTICO', TRUE, 'llamada_con_argumento_dinamico', '["SqlCommand", "SqlDataAdapter", "OleDbCommand", "OdbcCommand", "MySqlCommand", "NpgsqlCommand", "OracleCommand", "CommandText", "ExecuteSqlRaw", "ExecuteSqlRawAsync", "FromSqlRaw", "ExecuteSqlCommand"]'::jsonb, '{"modo": "concatenado"}'::jsonb, 'A03:2021', 'A05:2025', 'CWE-89', '{detalle} La consulta SQL se arma concatenando datos (CWE-89).', 'Usar SqlParameter / consultas parametrizadas o LINQ con Entity Framework (FromSqlInterpolated).', TRUE),
    ('SEG-003', 'Inyección de comandos del sistema operativo', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'CRÍTICO', TRUE, 'llamada_con_argumento_dinamico', '["Process.Start", "ProcessStartInfo"]'::jsonb, '{"modo": "concatenado"}'::jsonb, 'A03:2021', 'A05:2025', 'CWE-78', '{detalle} Un atacante podría ejecutar comandos arbitrarios (CWE-78).', 'Evitar invocar el intérprete de comandos; validar la entrada contra una lista blanca y pasar argumentos por ArgumentList.', TRUE),
    ('SEG-004', 'Caracteres especiales peligrosos junto a datos externos', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'ADVERTENCIA', TRUE, 'concatenacion_con_patron', '["''", "\"", ";", "--", "/*", "*/", "../", "..\\", "<script", "<", ">", "|", "&&", "`", "$(", "%00"]'::jsonb, '{}'::jsonb, 'A03:2021', 'A05:2025', 'CWE-74', '{detalle}', 'Validar y escapar la entrada según su destino (SQL, HTML, ruta, comando) o usar APIs que separen datos de instrucciones.', TRUE),
    ('SEG-005', 'Recorrido de directorios (Path Traversal)', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'CRÍTICO', TRUE, 'llamada_con_argumento_dinamico', '["File.ReadAllText", "File.ReadAllBytes", "File.ReadAllLines", "File.WriteAllText", "File.WriteAllBytes", "File.Open", "File.OpenRead", "File.Delete", "File.Copy", "File.Move", "FileStream", "StreamReader", "StreamWriter", "PhysicalFile", "Directory.Delete"]'::jsonb, '{"modo": "concatenado"}'::jsonb, 'A01:2021', 'A01:2025', 'CWE-22', '{detalle} La ruta se arma con datos externos (CWE-22).', 'Usar Path.GetFileName y verificar que la ruta final (Path.GetFullPath) quede dentro del directorio permitido.', TRUE),
    ('SEG-006', 'Solicitud a URL controlada por el usuario (SSRF)', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'ADVERTENCIA', TRUE, 'llamada_con_argumento_dinamico', '["GetAsync", "GetStringAsync", "GetByteArrayAsync", "GetStreamAsync", "PostAsync", "PutAsync", "WebRequest.Create", "HttpWebRequest.Create", "DownloadString", "DownloadData", "OpenRead"]'::jsonb, '{"modo": "dinamico", "solo_primer_argumento": true}'::jsonb, 'A10:2021', 'A01:2025', 'CWE-918', '{detalle} El servidor hace una petición a una dirección que no es fija (CWE-918).', 'Validar la URL contra una lista blanca de dominios y bloquear direcciones internas (localhost, 169.254.x.x, redes privadas).', TRUE),
    ('SEG-007', 'Algoritmo criptográfico débil u obsoleto', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'CRÍTICO', TRUE, 'llamada_a_metodo', '["MD5.Create", "MD5CryptoServiceProvider", "SHA1.Create", "SHA1Managed", "SHA1CryptoServiceProvider", "DES.Create", "DESCryptoServiceProvider", "TripleDES.Create", "TripleDESCryptoServiceProvider", "RC2.Create", "RC2CryptoServiceProvider"]'::jsonb, '{}'::jsonb, 'A02:2021', 'A04:2025', 'CWE-327', '{detalle} El algoritmo se considera roto o débil (CWE-327).', 'Usar SHA-256 o superior para integridad, AES-GCM para cifrado y PBKDF2/Argon2 para contraseñas.', TRUE),
    ('SEG-008', 'Generador de números aleatorios no criptográfico', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'BAJO', TRUE, 'llamada_a_metodo', '["Random"]'::jsonb, '{}'::jsonb, 'A02:2021', 'A04:2025', 'CWE-330', '{detalle} System.Random es predecible si se usa para tokens o claves (CWE-330).', 'Para valores de seguridad usar RandomNumberGenerator.GetBytes / GetInt32.', TRUE),
    ('SEG-009', 'Deserialización insegura', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'CRÍTICO', TRUE, 'llamada_a_metodo', '["BinaryFormatter", "SoapFormatter", "NetDataContractSerializer", "LosFormatter", "ObjectStateFormatter", "JavaScriptSerializer"]'::jsonb, '{}'::jsonb, 'A08:2021', 'A08:2025', 'CWE-502', '{detalle} Deserializar datos no confiables puede ejecutar código (CWE-502).', 'Reemplazar por System.Text.Json con tipos explícitos; nunca deserializar tipos arbitrarios.', TRUE),
    ('SEG-010', 'Validación de tokens JWT desactivada', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'CRÍTICO', TRUE, 'asignacion_insegura', '["ValidateIssuer=false", "ValidateAudience=false", "ValidateLifetime=false", "ValidateIssuerSigningKey=false", "RequireSignedTokens=false", "RequireExpirationTime=false"]'::jsonb, '{}'::jsonb, 'A07:2021', 'A07:2025', 'CWE-287', 'Se desactiva una validación del token: {detalle} (CWE-287).', 'Mantener activas todas las validaciones de TokenValidationParameters.', TRUE),
    ('SEG-011', 'Configuración de seguridad desactivada en el código', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'ADVERTENCIA', TRUE, 'asignacion_insegura', '["RequireHttpsMetadata=false", "HttpOnly=false", "SecurePolicy=None", "ServerCertificateValidationCallback=true", "ServerCertificateCustomValidationCallback=true", "Mode=ECB"]'::jsonb, '{}'::jsonb, 'A05:2021', 'A02:2025', 'CWE-16', 'Configuración insegura: {detalle}', 'Exigir HTTPS, cookies HttpOnly/Secure, validar certificados y no usar el modo de cifrado ECB.', TRUE),
    ('SEG-012', 'Deserialización JSON con tipos arbitrarios', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'CRÍTICO', TRUE, 'asignacion_insegura', '["TypeNameHandling=All", "TypeNameHandling=Auto", "TypeNameHandling=Objects", "TypeNameHandling=Arrays"]'::jsonb, '{}'::jsonb, 'A08:2021', 'A08:2025', 'CWE-502', '{detalle} Newtonsoft.Json podrá instanciar cualquier tipo indicado en el JSON (CWE-502).', 'Usar TypeNameHandling.None o un SerializationBinder con lista blanca de tipos.', TRUE),
    ('SEG-013', 'Política CORS abierta a cualquier origen', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'ADVERTENCIA', TRUE, 'llamada_a_metodo', '["AllowAnyOrigin", "SetIsOriginAllowed"]'::jsonb, '{}'::jsonb, 'A05:2021', 'A02:2025', 'CWE-942', '{detalle} Cualquier sitio podría consumir la API desde el navegador (CWE-942).', 'Declarar explícitamente los orígenes permitidos con WithOrigins(...).', TRUE),
    ('SEG-014', 'Controlador sin control de acceso', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'ADVERTENCIA', TRUE, 'controlador_sin_atributo', '["Authorize", "AllowAnonymous"]'::jsonb, '{"alcance": "clase"}'::jsonb, 'A01:2021', 'A01:2025', 'CWE-862', '{detalle} Sus acciones quedan expuestas sin autenticación (CWE-862).', 'Agregar [Authorize] al controlador (o [AllowAnonymous] solo en las acciones públicas).', TRUE),
    ('SEG-015', 'Acción que modifica datos sin protección CSRF', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'ADVERTENCIA', TRUE, 'controlador_sin_atributo', '["ValidateAntiForgeryToken", "AutoValidateAntiforgeryToken"]'::jsonb, '{"alcance": "accion", "excluir_si": ["ApiController"]}'::jsonb, 'A01:2021', 'A01:2025', 'CWE-352', '{detalle} Un sitio externo podría enviar la petición en nombre del usuario (CWE-352).', 'Agregar [ValidateAntiForgeryToken] a la acción o AutoValidateAntiforgeryToken como filtro global.', TRUE),
    ('SEG-016', 'Excepción ignorada o capturada de forma genérica', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'ADVERTENCIA', TRUE, 'excepcion_mal_manejada', '["Exception", "SystemException"]'::jsonb, '{}'::jsonb, 'A09:2021', 'A10:2025', 'CWE-390', '{detalle} Los errores pasan inadvertidos y el sistema puede quedar en un estado inconsistente (CWE-390).', 'Capturar excepciones específicas, registrarlas con ILogger y relanzar o responder de forma controlada.', TRUE),
    ('SEG-017', 'Datos sensibles escritos en el registro (log)', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'ADVERTENCIA', TRUE, 'llamada_con_dato_sensible', '["LogInformation", "LogDebug", "LogTrace", "LogWarning", "LogError", "LogCritical", "Console.WriteLine", "Debug.WriteLine", "Trace.WriteLine"]'::jsonb, '{"palabras": ["password", "contrasena", "pwd", "token", "secret", "apikey", "tarjeta", "cvv"]}'::jsonb, 'A09:2021', 'A09:2025', 'CWE-532', '{detalle} Los registros quedan expuestos a quien tenga acceso a ellos (CWE-532).', 'No registrar secretos ni datos personales; enmascararlos antes de escribir el log.', TRUE),
    ('SEG-018', 'Dependencia vulnerable, obsoleta o sin versión fija', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'ADVERTENCIA', TRUE, 'paquete_vulnerable', '["Newtonsoft.Json<13.0.1", "System.Text.Encodings.Web<4.5.1", "log4net<2.0.10", "System.Data.SqlClient"]'::jsonb, '{"version_flotante": true}'::jsonb, 'A06:2021', 'A03:2025', 'CWE-1104', '{detalle}', 'Actualizar a una versión sin vulnerabilidades conocidas (revisar con ''dotnet list package --vulnerable'') y fijar la versión.', TRUE),
    ('SEG-019', 'Configuración insegura en appsettings.json', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'ADVERTENCIA', TRUE, 'configuracion_insegura', '["AllowedHosts=*", "DetailedErrors=true", "*:RequireHttpsMetadata=false", "Logging:LogLevel:Default=Trace"]'::jsonb, '{}'::jsonb, 'A05:2021', 'A02:2025', 'CWE-16', 'Ajuste inseguro: {detalle}', 'Restringir AllowedHosts, desactivar errores detallados y el registro excesivo en producción.', TRUE),
    ('SEG-020', 'Secreto en archivo de configuración', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'CRÍTICO', TRUE, 'secreto_en_configuracion', '["password", "pwd", "secret", "apikey", "api_key", "token", "clientsecret"]'::jsonb, '{"marcadores_en_valor": ["password=", "pwd="]}'::jsonb, 'A07:2021', 'A07:2025', 'CWE-798', '{detalle} Cualquiera con acceso al repositorio puede leerlo (CWE-798).', 'Usar variables de entorno, User Secrets o Azure Key Vault y dejar el valor vacío en el repositorio.', TRUE),
    ('SEG-021', 'Contraseña comparada en texto plano', 'Módulo 1: Seguridad', 'Seguridad (OWASP)', 'CRÍTICO', TRUE, 'comparacion_texto_plano', '["password", "contrasena", "pwd", "clave"]'::jsonb, '{"excepto_si_contiene": ["hash", "verify", "null"]}'::jsonb, 'A04:2021', 'A06:2025', 'CWE-256', '{detalle} Indica que la contraseña se guarda o transmite sin hash (CWE-256).', 'Guardar solo un hash con sal (PasswordHasher de ASP.NET Identity, PBKDF2) y comparar con su verificador.', TRUE),
    ('PERF-001', 'Variables locales declaradas sin utilización', 'Módulo 2: Rendimiento', 'Rendimiento (.NET)', 'ADVERTENCIA', TRUE, 'variable_no_usada', '["_"]'::jsonb, '{}'::jsonb, NULL, NULL, 'CWE-563', '{detalle} Indica código muerto o un cálculo desechado.', 'Eliminar la declaración o utilizar el resultado calculado.', TRUE),
    ('MEM-004', 'Clases IDisposable sin bloque ''using'' o cierre formal', 'Módulo 3: Memoria', 'Gestión de Memoria', 'ADVERTENCIA', TRUE, 'recurso_sin_liberar', '["SqlConnection", "SqlCommand", "SqlDataReader", "FileStream", "StreamReader", "StreamWriter", "HttpClient", "MemoryStream", "Timer", "Process", "BinaryReader", "BinaryWriter"]'::jsonb, '{}'::jsonb, NULL, 'A10:2025', 'CWE-404', '{detalle} El recurso puede quedar abierto y agotar conexiones o memoria.', 'Declarar con ''using var'' o envolver en un bloque ''using''.', TRUE),
    ('GOV-001', 'Falta de nomenclatura estándar PascalCase', 'Módulo 4: Gobierno', 'Gobierno Estructural', 'BAJO', TRUE, 'nomenclatura', '["^[A-Z][a-zA-Z0-9]*$"]'::jsonb, '{"tipos": ["property"], "modificador": "public"}'::jsonb, NULL, NULL, NULL, '{detalle} Las guías de estilo de .NET usan PascalCase para miembros públicos.', 'Renombrar siguiendo PascalCase (p. ej. ''UserName'').', TRUE)
ON CONFLICT (codigo_regla) DO UPDATE SET
    descripcion = EXCLUDED.descripcion, modulo = EXCLUDED.modulo, categoria = EXCLUDED.categoria,
    severidad = EXCLUDED.severidad, tipo_deteccion = EXCLUDED.tipo_deteccion, patrones = EXCLUDED.patrones,
    parametros = EXCLUDED.parametros, owasp_2021 = EXCLUDED.owasp_2021, owasp_2025 = EXCLUDED.owasp_2025,
    cwe = EXCLUDED.cwe, mensaje = EXCLUDED.mensaje, recomendacion = EXCLUDED.recomendacion, predefinida = TRUE
WHERE regla.tipo_deteccion IS NULL;

COMMIT;
