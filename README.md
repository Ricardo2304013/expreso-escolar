# 🚌 Expreso Escolar — Sistema de Gestión de Transporte Escolar

## Tecnologías
- **Python 3.10+**
- **Django 4.2**
- **SQLite** (base de datos incluida)

## Instalación y ejecución

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Ejecutar el servidor
```bash
py manage.py runserver
```

### 3. Abrir en el navegador
```
http://127.0.0.1:8000
```

---

## 👤 Usuarios de prueba incluidos

| Rol | Correo | Contraseña |
|-----|--------|------------|
| 🔑 Administrador | admin@expreso.com | 12345678 |
| 🚌 Transportista | trans@expreso.com | 12345678 |
| 👨‍👩‍👦 Padre | padre@expreso.com | 12345678 |

---

## 🗂️ Estructura del Proyecto
```
expreso_escolar/
├── core/                  ← Aplicación principal
│   ├── models.py          ← Modelos de base de datos
│   ├── views.py           ← Lógica de las páginas
│   ├── forms.py           ← Formularios
│   ├── admin.py           ← Panel de administración
│   └── decorators.py      ← Control de acceso por rol
├── templates/             ← Diseño HTML de todas las páginas
├── static/css/style.css   ← Estilos CSS
├── manage.py              ← Comando principal de Django
└── db.sqlite3             ← Base de datos SQLite
```

## 📋 Módulos del sistema
- ✅ Autenticación (login, registro, logout)
- ✅ Dashboard por rol (admin, transportista, padre)
- ✅ Gestión de estudiantes
- ✅ Gestión de expresos (vehículos)
- ✅ Asignaciones con flujo de aceptación/rechazo
- ✅ Reporte de incidencias
- ✅ Gestión de usuarios
- ✅ Panel administrativo de Django
