#!/usr/bin/env python3
"""
Monitor de Citas — Embajada de España (citaconsular.es)
Revisa si el formulario de citas está habilitado y envía alerta por Telegram.
Usa Playwright (Chrome headless) porque la página carga con JS (Angular widget).
"""

import os
import sys
import subprocess
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ── Configuración ──────────────────────────────────────────────
TARGET_URL = os.environ.get(
    "TARGET_URL",
    "https://www.citaconsular.es/es/hosteds/widgetdefault/22091b5b8d43b89fb226cabb272a844f9/#services",
)
TELEGRAM_TOKEN = os.environ["8735978634:AAGySL_PXefOAokRI6-egAd2-lBlYiyCL20"]
TELEGRAM_CHAT_ID = os.environ["8614326857"]
STATE_FILE = "state.txt"

CLOSED_KEYWORDS = [
    "no hay citas disponibles",
    "no existen citas disponibles",
    "servicio no disponible",
    "fuera de servicio",
    "temporalmente cerrado",
    "actualmente no hay citas",
    "no se pueden solicitar citas",
    "sistema cerrado",
    "sin disponibilidad",
    "no disponible en este momento",
    "no es posible solicitar cita",
    "agenda cerrada",
    "cerrado temporalmente",
]


# ── Telegram ───────────────────────────────────────────────────
def send_telegram(text: str) -> None:
    """Envía un mensaje a Telegram usando la API de bots."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        print("[Telegram] Mensaje enviado correctamente.")
    except Exception as exc:
        print(f"[Telegram] Error al enviar mensaje: {exc}")


# ── Estado ─────────────────────────────────────────────────────
def read_state() -> str:
    """Lee el último estado guardado en state.txt."""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "unknown"


def write_state(state: str) -> None:
    """Guarda el nuevo estado en state.txt."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(state)


def git_commit_state() -> None:
    """Hace commit y push del archivo de estado para persistirlo en el repo."""
    try:
        subprocess.run(["git", "config", "user.name", "cita-monitor[bot]"], check=True)
        subprocess.run(
            ["git", "config", "user.email", "bot@cita-monitor.local"], check=True
        )
        subprocess.run(["git", "add", STATE_FILE], check=True)
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], capture_output=True
        )
        if result.returncode != 0:  # Hay cambios staged
            subprocess.run(
                ["git", "commit", "-m", f"state: update to latest"],
                check=True,
            )
            subprocess.run(["git", "push"], check=True)
            print("[Git] Estado actualizado en el repositorio.")
        else:
            print("[Git] Sin cambios en state.txt, nada que commitear.")
    except Exception as exc:
        print(f"[Git] Error al hacer commit/push: {exc}")


# ── Detección del estado ───────────────────────────────────────
def detect_state(page) -> str:
    """
    Detecta el estado del formulario usando múltiples métodos en cascada:
    1. Keywords de cierre en el texto visible
    2. Botón 'Continuar' habilitado/deshabilitado
    3. Botones de tipo submit
    4. Campos de formulario activos
    """
    try:
        body_text = page.inner_text("body").lower()
    except Exception:
        body_text = ""

    # ── Método 1: Keywords de cierre ───────────────────────────
    for keyword in CLOSED_KEYWORDS:
        if keyword in body_text:
            print(f'[Detección] Keyword encontrada: "{keyword}"')
            return "disabled"

    # ── Método 2: Botón "Continuar" ───────────────────────────
    try:
        continuar_btns = page.query_selector_all(
            'button:has-text("Continuar"), '
            'input[type="submit"][value*="ontinuar"], '
            'a:has-text("Continuar")'
        )
        for btn in continuar_btns:
            is_disabled = btn.get_attribute("disabled") is not None
            aria_disabled = btn.get_attribute("aria-disabled")
            classes = btn.get_attribute("class") or ""
            if is_disabled or aria_disabled == "true" or "disabled" in classes:
                print('[Detección] Botón "Continuar" encontrado pero DESHABILITADO.')
                return "disabled"
            else:
                print('[Detección] Botón "Continuar" encontrado y HABILITADO.')
                return "active"
    except Exception as exc:
        print(f"[Detección] Error buscando botón Continuar: {exc}")

    # ── Método 3: Botones submit ──────────────────────────────
    try:
        submits = page.query_selector_all(
            'button[type="submit"], input[type="submit"]'
        )
        enabled_submits = []
        for s in submits:
            if s.get_attribute("disabled") is None:
                enabled_submits.append(s)
        if enabled_submits:
            print(
                f"[Detección] {len(enabled_submits)} botón(es) submit habilitado(s)."
            )
            return "active"
    except Exception as exc:
        print(f"[Detección] Error buscando botones submit: {exc}")

    # ── Método 4: Campos de formulario activos ─────────────────
    try:
        fields = page.query_selector_all(
            "input:not([type=hidden]):not([disabled]), "
            "select:not([disabled]), "
            "textarea:not([disabled])"
        )
        active_fields = len(fields)
        print(f"[Detección] {active_fields} campo(s) de formulario activo(s).")
        if active_fields >= 2:
            return "active"
    except Exception as exc:
        print(f"[Detección] Error contando campos de formulario: {exc}")

    return "unknown"


# ── Notificaciones ─────────────────────────────────────────────
def notify_active() -> None:
    """Envía la alerta de formulario habilitado."""
    message = (
        "🚨 <b>¡CITA EN LA EMBAJADA DISPONIBLE!</b> 🚨\n\n"
        "✅ El formulario está <b>HABILITADO AHORA</b>\n\n"
        f'🔗 <a href="{TARGET_URL}">👉 SOLICITAR CITA AHORA</a>\n\n'
        "⚡ <b>¡Date prisa, los horarios se agotan rápido!</b>"
    )
    send_telegram(message)


def notify_disabled() -> None:
    """Envía una notificación cuando el formulario vuelve a cerrarse."""
    message = (
        "🔴 <b>Formulario CERRADO de nuevo</b>\n\n"
        "El formulario de citas ha vuelto al estado deshabilitado.\n"
        "Seguiré revisando cada 5 minutos."
    )
    send_telegram(message)


# ── Main ───────────────────────────────────────────────────────
def main() -> None:
    print(f"[Monitor] Revisando: {TARGET_URL}")

    previous_state = read_state()
    print(f"[Monitor] Estado anterior: {previous_state}")

    current_state = "unknown"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        try:
            print("[Monitor] Cargando la página...")
            page.goto(TARGET_URL, wait_until="networkidle", timeout=30000)

            # Esperar a que el widget Angular cargue completamente
            page.wait_for_timeout(5000)

            print("[Monitor] Página cargada. Analizando estado...")
            current_state = detect_state(page)

        except PlaywrightTimeout:
            print("[Monitor] ⚠️  Timeout al cargar la página.")
            current_state = "unknown"
        except Exception as exc:
            print(f"[Monitor] ⚠️  Error inesperado: {exc}")
            current_state = "unknown"
        finally:
            browser.close()

    print(f"[Monitor] Estado actual : {current_state}")

    # ── Comparar y notificar ───────────────────────────────────
    if current_state == "active" and previous_state != "active":
        print("[Monitor] 🚨 ¡CAMBIO DETECTADO! → Formulario HABILITADO")
        notify_active()
    elif current_state == "disabled" and previous_state == "active":
        print("[Monitor] 🔴 Formulario volvió a cerrarse.")
        notify_disabled()
    else:
        print("[Monitor] Sin cambios. Todo bien.")

    # ── Guardar estado ─────────────────────────────────────────
    if current_state != "unknown":
        write_state(current_state)
        git_commit_state()
    else:
        print("[Monitor] Estado 'unknown' — no se actualiza state.txt.")


if __name__ == "__main__":
    main()
