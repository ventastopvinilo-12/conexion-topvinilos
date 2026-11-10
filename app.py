import os
from flask import Flask

app = Flask(__name__)

@app.get("/")
def inicio():
    if os.environ.get("ML_CLIENT_ID"):
        estado = "Client ID configurado correctamente."
    else:
        estado = "Falta configurar el Client ID en Render."

    return f"""
    <h1>Conector de Top Vinilos</h1>
    <p>El servidor está funcionando.</p>
    <p>{estado}</p>
    <p>Todavía no está conectado a Mercado Libre.</p>
    """
