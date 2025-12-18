# 🎓 Plataforma Académica Multicolegios – Django

Sistema académico y administrativo desarrollado en **Django**, diseñado bajo una **arquitectura multicolegios (multi-tenant)**, que permite a múltiples instituciones educativas operar de forma **independiente** dentro de un solo proyecto.

Cada colegio funciona de manera aislada mediante **dominio o subdominio**, compartiendo el mismo código base pero con **datos completamente separados**.

---

## 🚀 Características Principales

- ✅ Arquitectura **multicolegios (multi-tenant)**
- 🌐 Separación por **dominio / subdominio**
- 🏫 Gestión independiente por colegio
- 👨‍🎓 Módulo Académico
- 💰 Módulo de Cartera y Pagos
- 🧾 Módulo Administrativo
- 📊 Tablero informativo
- 🌍 Sitio público por colegio
- 🔐 Roles y permisos por usuario
- 🛡️ Middleware para detección automática del colegio

---

## 🏗️ Arquitectura Multicolegios

- Un solo proyecto Django
- Una sola base de datos
- Modelo central `School`
- Todos los modelos principales están relacionados con `school`
- Middleware detecta el colegio según el dominio
- El **Admin de Django** funciona filtrando automáticamente por colegio

### Ejemplo de dominios