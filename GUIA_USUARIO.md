# 📝 Guía de Uso - Frío Natural

## Cómo Agregar un Usuario Admin

### Opción 1: Usando el Script Python (RECOMENDADO)

1. Abre una terminal en la carpeta `BACK END`
2. Ejecuta el siguiente comando:

```bash
python add_admin.py email@example.com username password "Nombre Completo"
```

**Ejemplos:**

```bash
# Agregar admin@admin.com como admin
python add_admin.py admin@admin.com admingc4td4sxo securepass123 "Admin Admin"

# Agregar otro admin
python add_admin.py nuevo@admin.com newadmin password123 "Nuevo Admin"
```

**Parámetros:**
- `email`: Correo electrónico único
- `username`: Nombre de usuario único (sin espacios)
- `password`: Contraseña segura
- `"Nombre Completo"`: Nombre real (opcional, default: "Admin")

### Opción 2: Desde la Base de Datos Directamente

Si prefieres usar una herramienta de base de datos como SQLite Browser:

1. Abre `frio_natural.db` con SQLite Browser
2. Ve a la tabla `user`
3. Inserta un registro con:
   - `email`: tu_email@admin.com
   - `username`: tuusername
   - `hashed_password`: Hash bcrypt de tu contraseña
   - `full_name`: Tu nombre
   - `role`: **admin** (esto es lo importante)
   - `is_active`: 1 (true)
   - `created_at`: Fecha actual

---

## Respecto a la Recuperación de Contraseña

❌ **NO, actualmente NO está implementado el sistema de email.**

El enlace de recuperación **NO llega a ningún correo** porque:

1. **No hay servidor de email configurado** - Se necesitaría SMTP (Gmail, SendGrid, etc.)
2. **No hay endpoint de recuperación** - No existe en la API
3. **No hay generación de tokens** - Se necesitarían tokens únicos y con expiración

### ¿Quieres que lo implemente?

Si deseas agregar recuperación de contraseña, necesitaríamos:
- Configurar un servicio SMTP (ej: Gmail)
- Crear endpoint `/api/auth/forgot-password`
- Generar tokens de recuperación con expiración
- Crear página HTML para reset de contraseña
- Implementar envío de emails

**Avísame si lo quieres y lo implemento!**

---

## Menú de Usuario - NUEVO

El menú de usuario ahora tiene una interfaz mejorada:

- **Haz clic en el avatar** (icono de usuario) en la esquina superior derecha
- **Se abre un dropdown elegante** con:
  - Nombre y email del usuario
  - Opción "Mi Perfil"
  - Opción "Panel Admin" (solo si eres admin)
  - Opción "Cerrar Sesión"

### Características:
✅ Se cierra automáticamente si haces clic fuera
✅ Diseño moderno con gradientes
✅ Animaciones suaves
✅ Responsive en móviles

---

## Problemas Arreglados

### ✅ Visualización del Usuario
- **Antes**: Se mostraba `{"id":1,"email":"admin@admin.com",...}` (JSON completo)
- **Después**: Se muestra `"Bienvenido, Admin Admin"` (Solo el nombre)

Esto se arregló en:
- `catalogo.html`
- `promociones.html`
- `index.html` (también mejorado)

---

## Resumen de Archivos Modificados

### Nuevos:
- ✅ `BACK END/add_admin.py` - Script para agregar admins

### Modificados:
- ✅ `FRONT END/index.html` - Nuevo dropdown de usuario elegante
- ✅ `FRONT END/catalogo.html` - Arreglada visualización del usuario
- ✅ `FRONT END/promociones.html` - Arreglada visualización del usuario

---

## Credenciales de Prueba

**Admin por defecto:**
- Email: `admin@admin.com`
- Usuario: `admingc4td4sxo`
- Contraseña: `admin123`

---

¿Tienes más preguntas? ¡Pregunta sin problemas! 😊
