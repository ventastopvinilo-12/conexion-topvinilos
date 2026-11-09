import os
from flask import Flask

app = Flask(__name__)

@app.get("/")
def inicio():
    return """
    <h1>Conector de Top Vinilos</h1>
    <p>El servidor está funcionando.</p>
    <p>Todavía no está conectado a Mercado Libre.</p>
    """

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=puerto)
