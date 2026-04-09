from flask import Flask, request, jsonify, send_file
import subprocess
import os
import threading
from pathlib import Path
import time

app = Flask(__name__)

INPUT_DIR = os.getenv("INPUT_DIR", "/app/input")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/app/output")

processing_status = {"running": False, "last_result": None}


def run_processor():
    processing_status["running"] = True
    processing_status["last_result"] = None
    result = subprocess.run(
        ["python3", "process.py", "--input", INPUT_DIR, "--output", OUTPUT_DIR],
        capture_output=True, text=True
    )
    processing_status["running"] = False
    processing_status["last_result"] = {
        "returncode": result.returncode,
        "stdout": result.stdout[-1000:],
        "stderr": result.stderr[-500:] if result.returncode != 0 else ""
    }


@app.route("/", methods=["GET"])
def index():
    input_files = list(Path(INPUT_DIR).glob("*.mp4")) + list(Path(INPUT_DIR).glob("*.mov"))
    output_files = list(Path(OUTPUT_DIR).glob("*.mp4"))
    return jsonify({
        "status": "online",
        "input_videos": len(input_files),
        "output_videos": len(output_files),
        "processor_running": processing_status["running"]
    })


@app.route("/upload", methods=["POST"])
def upload():
    """Recibe un video y lo guarda en input."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    Path(INPUT_DIR).mkdir(parents=True, exist_ok=True)
    filename = f"{int(time.time())}_{file.filename}"
    filepath = os.path.join(INPUT_DIR, filename)
    file.save(filepath)

    return jsonify({"message": "Uploaded", "filename": filename}), 200


@app.route("/process", methods=["POST"])
def trigger_process():
    if processing_status["running"]:
        return jsonify({"error": "Processor already running"}), 409

    thread = threading.Thread(target=run_processor)
    thread.daemon = True
    thread.start()
    return jsonify({"message": "Processing started"}), 202


@app.route("/status", methods=["GET"])
def status():
    return jsonify(processing_status)


@app.route("/outputs", methods=["GET"])
def list_outputs():
    """Lista los videos procesados disponibles."""
    files = list(Path(OUTPUT_DIR).glob("*.mp4"))
    return jsonify({
        "files": [f.name for f in files]
    })


@app.route("/download/<filename>", methods=["GET"])
def download(filename):
    """Descarga un video procesado."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    return send_file(filepath, as_attachment=True)


@app.route("/clear", methods=["POST"])
def clear():
    """Limpia input y output."""
    for f in Path(INPUT_DIR).glob("*"):
        f.unlink()
    for f in Path(OUTPUT_DIR).glob("*"):
        f.unlink()
    return jsonify({"message": "Cleared"}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
