import hmac
import os
import secrets
import time
from urllib.parse import urlencode
from flask_limiter import Limiter
from flask_wtf.csrf import CSRFProtect, generate_csrf


from flask_limiter.util import get_remote_address

import requests
from flask import Flask, redirect, request, session

app = Flask(__name__)
csrf = CSRFProtect(app)

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri="memory://",
)

@app.before_request
def mantenimiento():
    return "Conector en mantenimiento. La conexión todavía no está habilitada.", 503

client_secret = os.environ.get("ML_CLIENT_SECRET", "")
app.secret_key = os.environ.get("SESSION_SECRET")


app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

# Solo para esta prueba: se pierde al reiniciar el servidor.
conexion = {"access_token": None}


@app.get("/")
def inicio():
    if not session.get("autenticado"):
        return f"""
        <h1>Conector de Top Vinilos</h1>
        <p>Ingresá la contraseña que configuraste en Render.</p>
        <form method="post" action="/ingresar">
          <input type="hidden" name="csrf_token" value="{generate_csrf()}">
          <input type="password" name="password" required>
          <button type="submit">Ingresar</button>
        </form>
        """

    if conexion["access_token"]:
        estado = "Cuenta conectada para esta prueba."
    else:
        estado = "La cuenta todavía no está conectada."

    return f"""
    <h1>Conector de Top Vinilos</h1>
    <p>{estado}</p>
    <p>Esta prueba no lee ni modifica campañas.</p>
    <form method="post" action="/conectar">
      <input type="hidden" name="csrf_token" value="{generate_csrf()}">
      <button type="submit">Conectar con Mercado Libre</button>
    </form>
    """


@app.post("/ingresar")
@limiter.limit("5 per minute")
def ingresar():
    password = request.form.get("password", "")
    password_guardada = os.environ.get("PANEL_PASSWORD", "")

    if not password_guardada or not hmac.compare_digest(
        password.encode(), password_guardada.encode()
    ):
        return "Contraseña incorrecta o no configurada.", 403

    session.clear()
    session["autenticado"] = True
    return redirect("/")


@app.post("/conectar")
def conectar():
    if not session.get("autenticado"):
        return redirect("/")

    client_id = os.environ.get("ML_CLIENT_ID", "")
    redirect_uri = os.environ.get("ML_REDIRECT_URI", "")

    if not client_id or not client_secret or not redirect_uri:
        return "Falta configurar una variable en Render.", 500

    estado = secrets.token_urlsafe(32)
    session["oauth_estado"] = estado
    session["oauth_inicio"] = time.time()

    parametros = urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": estado,
    })

    return redirect(
        "https://auth.mercadolibre.com.ar/authorization?" + parametros
    )


@app.get("/callback")
def callback():
    estado_esperado = session.pop("oauth_estado", "")
    inicio = session.pop("oauth_inicio", 0)
    estado_recibido = request.args.get("state", "")
    codigo = request.args.get("code", "")

    if not session.get("autenticado"):
        return "Iniciá sesión en el panel y volvé a intentarlo.", 403

    if (
        not estado_esperado
        or not hmac.compare_digest(estado_esperado, estado_recibido)
        or time.time() - inicio > 600
        or not codigo
    ):
        return "La autorización no pudo verificarse. Volvé al inicio.", 400

    try:
        respuesta = requests.post(
            "https://api.mercadolibre.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": os.environ.get("ML_CLIENT_ID", ""),
                "client_secret": client_secret,
                "code": codigo,
                "redirect_uri": os.environ.get("ML_REDIRECT_URI", ""),
            },
            timeout=20,
        )

        if not respuesta.ok:
            return "Mercado Libre rechazó la conexión. Volvé al inicio.", 400

        token = respuesta.json().get("access_token")
        if not token:
            return "No se recibió un token de acceso.", 400

        conexion["access_token"] = token
        return redirect("/")

    except (requests.RequestException, ValueError):
        return "No se pudo completar la conexión. Intentá nuevamente.", 500
