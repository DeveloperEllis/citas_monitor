# 🕵️ Monitor de Citas — Embajada de España

Sistema automático que revisa cada 5 minutos si el formulario de citas de la Embajada de España en [citaconsular.es](https://www.citaconsular.es) está habilitado y envía una alerta instantánea por **Telegram**.

## Arquitectura

| Componente | Función | Tecnología |
|---|---|---|
| **GitHub Actions** | Ejecuta el script cada 5 min, gratis 24/7 | YAML workflow |
| **Python + Playwright** | Abre Chrome headless, carga el widget JS y detecta el estado | `playwright`, `requests` |
| **Telegram Bot** | Envía notificación al celular cuando se habilita el formulario | API de Telegram |

> ⚠️ La página usa un widget **Angular** (JavaScript). Un simple `requests.get()` no sirve porque el contenido se renderiza con JS. Por eso se usa **Playwright** con un Chrome real headless.

## Estructura del Proyecto

```
cita-monitor/
├── .github/workflows/monitor.yml   ← Automatización cada 5 min
├── monitor.py                      ← Script principal (Playwright)
├── requirements.txt                ← Dependencias Python
├── state.txt                       ← Último estado detectado
└── README.md
```

## Configuración

### 1. Crear Bot de Telegram

1. Abrir **@BotFather** en Telegram → `/newbot`
2. Nombre: `Monitor Citas España`
3. Username: `monitor_citas_esp_bot` (debe terminar en `bot`)
4. Guardar el **TOKEN** que entrega BotFather

### 2. Obtener Chat ID

1. Enviar cualquier mensaje al bot recién creado
2. Visitar: `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Buscar `"chat": {"id": 123456789}` — ese es el **CHAT_ID**

### 3. Verificar

```
https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=Bot+funcionando
```

Si llega el mensaje a Telegram ✅, todo está bien.

### 4. Configurar GitHub Secrets

En el repositorio → **Settings → Secrets and variables → Actions**:

| Secret | Valor |
|---|---|
| `TELEGRAM_TOKEN` | Token del bot (ej: `7412365890:AAFjkds...`) |
| `TELEGRAM_CHAT_ID` | ID numérico del chat (ej: `987654321`) |
| `TARGET_URL` | URL de la página de citas |

### 5. Activar

1. Ir a **Actions** en el repositorio  
2. Habilitar workflows si es necesario  
3. Clic en **"Run workflow"** para probar manualmente  

## Detección en Cascada

El script usa 4 métodos para determinar el estado:

1. **Keywords de cierre** — busca frases como `"no hay citas disponibles"` en el texto
2. **Botón "Continuar"** — detecta si está habilitado o deshabilitado
3. **Botones submit** — revisa si existen y están activos
4. **Campos de formulario** — cuenta inputs/selects/textareas activos

## Notificación

Cuando el formulario se habilita:

```
🚨 ¡CITA EN LA EMBAJADA DISPONIBLE! 🚨
✅ El formulario está HABILITADO AHORA
🔗 👉 SOLICITAR CITA AHORA
⚡ ¡Date prisa, los horarios se agotan rápido!
```

## FAQ

- **¿Es gratis?** — Sí, repo público = minutos ilimitados en GitHub Actions
- **¿Cada cuánto revisa?** — Cada 5 min (288 veces/día)
- **¿Cómo detenerlo?** — Actions → ... → Disable workflow
- **¿Estado "unknown"?** — Aumentar `wait_for_timeout` en `monitor.py`

## Licencia

Uso personal.
