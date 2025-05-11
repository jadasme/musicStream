from flask import Flask, request, jsonify, send_file, render_template_string
from pymongo import MongoClient
from gridfs import GridFS
from bson.objectid import ObjectId
from dotenv import load_dotenv
import os
import io

# Cargar variables de entorno desde .env
load_dotenv()

app = Flask(__name__)

# Conexión a MongoDB
MONGO_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGO_URI)
db = client.musicstream
fs = GridFS(db)


@app.route("/")
def home():
    html = """
    <!doctype html>
    <title>MusicStream - Inicio</title>
    <h1>Bienvenido a MusicStream</h1>
    <ul>
        <li><a href="/subir">Subir nueva canción</a></li>
        <li><a href="/canciones">Ver canciones disponibles</a></li>
        <li><a href="/pingdb">Probar conexión a MongoDB</a></li>
    </ul>
    """
    return render_template_string(html)


# Probar la conexión a la db
@app.route("/pingdb")
def pingdb():
    try:
        client.admin.command("ping")
        return jsonify({"estado": "Conexión exitosa con MongoDB"})
    except Exception as e:
        return jsonify({"error": str(e)})


# Formulario para subir canción
@app.route("/subir", methods=["GET"])
def subir_form():
    html = """
    <!doctype html>
    <title>Subir canción</title>
    <h1>Subir nueva canción</h1>
    <form method=post enctype=multipart/form-data action="/subir">
      Título: <input type=text name=titulo><br>
      Artista: <input type=text name=artista><br>
      Álbum: <input type=text name=album><br>
      Género: <input type=text name=genero><br>
      Año: <input type=number name=anio><br>
      Duración (segundos): <input type=number name=duracion><br>
      Archivo MP3: <input type=file name=archivo><br><br>
      <input type=submit value=Subir>
    </form>
    <br><a href="/canciones">Ver canciones</a>
    """
    return render_template_string(html)


# Procesar la subida y gardar en GridFS
@app.route("/subir", methods=["POST"])
def subir_cancion():
    archivo = request.files.get("archivo")
    if not archivo or not archivo.filename.endswith(".mp3"):
        return jsonify({"error": "Archivo inválido o no proporcionado"}), 400

    # Guardar archivo en GridFS
    archivo_id = fs.put(
        archivo, filename=archivo.filename, content_type=archivo.content_type
    )

    # Guardar metadata en colección
    nueva_cancion = {
        "titulo": request.form.get("titulo"),
        "artista": request.form.get("artista"),
        "album": request.form.get("album"),
        "genero": request.form.get("genero"),
        "anio": int(request.form.get("anio")),
        "duracion_segundos": int(request.form.get("duracion")),
        "archivo_id": archivo_id,
    }

    resultado = db.canciones.insert_one(nueva_cancion)
    return jsonify(
        {
            "mensaje": "Canción agregada exitosamente",
            "id_cancion": str(resultado.inserted_id),
            "id_archivo": str(archivo_id),
        }
    )


# Reproducir lista de canciones
@app.route("/canciones")
def ver_canciones():
    canciones = list(db.canciones.find({}))
    html = "<h2>Canciones disponibles</h2><ul>"
    for c in canciones:
        html += f"""
            <li>
                <b>{c['titulo']}</b> - {c['artista']}<br>
                Álbum: {c['album']} | Género: {c['genero']} | Año: {c['anio']} | Duración: {c['duracion_segundos']}s<br>
                <audio controls src="/audio/{c['archivo_id']}"></audio>
            </li><br>
        """
    html += "</ul><br><a href='/subir'>Subir más canciones</a>"
    return html


# Servir archivos MP3
@app.route("/audio/<archivo_id>")
def servir_audio(archivo_id):
    try:
        file_data = fs.get(ObjectId(archivo_id))
        return send_file(io.BytesIO(file_data.read()), mimetype="audio/mpeg")
    except Exception as e:
        return jsonify({"error": f"No se pudo servir el archivo: {str(e)}"}), 404


if __name__ == "__main__":
    app.run(debug=True, port=3000, use_reloader=False)
