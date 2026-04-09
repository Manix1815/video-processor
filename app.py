from flask import Flask, request, jsonify, send_file
import subprocess
import os
import threading
import uuid
import time
from pathlib import Path
from collections import deque

app = Flask(__name__)

INPUT_DIR = os.getenv("INPUT_DIR", "/app/input")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/app/output")

# Cola y estado de jobs
job_queue = deque()
jobs = {}
queue_lock = threading.Lock()
is_processing = False


def process_worker():
    """Worker que procesa jobs de la cola uno a uno."""
    global is_processing
    while True:
        job_id = None
        with queue_lock:
            if job_queue:
                job_id = job_queue.popleft()

        if job_id is None:
            time.sleep(2)
            continue

        with queue_lock:
            jobs[job_id]["status"] = "processing"
            is_processing = True

        input_path = jobs[job_id]["input_path"]
        output_path = os.path.join(OUTPUT_DIR, f"processed_{job_id}.mp4")

        result = subprocess.run(
            ["python3", "process.py", "--file", input_path, "--output", OUTPUT_DIR],
            capture_output=True, text=True
        )

        with queue_lock:
            if result.returncode == 0:
                jobs[job_id]["status"] = "done"
                jobs[job_id]["output_path"] = output_path
            else:
                jobs[job_id]["status"] = "error"
                jobs[job_id]["error"] = result.stderr[-300:]
            is_processing = False

        # Limpia el input
        try:
            os.remove(input_path)
        except:
            pass


# Arranca el worker en background
worker_thread = threading.Thread(target=process_worker, daemon=True)
worker_thread.start()


@app.route("/", methods=["GET"])
def index():
    with queue_lock:
        pending = len([j for j in jobs.values() if j["status"] == "queued"])
        processing = len([j for j in jobs.values() if j["status"] == "processing"])
        done = len([j for j in jobs.values() if j["status"] == "done"])
    return jsonify({
        "status": "online",
        "queue_pending": pending,
        "processing": processing,
        "done": done
    })


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    Path(INPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    job_id = str(uuid.uuid4())[:8]
    filename = f"{job_id}_{file.filename}"
    input_path = os.path.join(INPUT_DIR, filename)
    file.save(input_path)

    with queue_lock:
        jobs[job_id] = {
            "status": "queued",
            "input_path": input_path,
            "output_path": None,
            "created_at": time.time()
        }
        job_queue.append(job_id)
        position = len(job_queue)

    return jsonify({
        "job_id": job_id,
        "status": "queued",
        "position": position
    }), 200


@app.route("/job/<job_id>", methods=["GET"])
def job_status(job_id):
    with queue_lock:
        if job_id not in jobs:
            return jsonify({"error": "Job not found"}), 404
        job = jobs[job_id].copy()
        position = list(job_queue).index(job_id) + 1 if job_id in job_queue else 0

    return jsonify({
        "job_id": job_id,
        "status": job["status"],
        "queue_position": position
    })


@app.route("/download/<job_id>", methods=["GET"])
def download(job_id):
    with queue_lock:
        if job_id not in jobs:
            return jsonify({"error": "Job not found"}), 404
        job = jobs[job_id].copy()

    if job["status"] != "done":
        return jsonify({
            "error": "Not ready",
            "status": job["status"]
        }), 425

    # Busca el archivo procesado
    output_file = os.path.join(OUTPUT_DIR, f"processed_{job_id}.mp4")
    
    # Si no existe con job_id, busca por nombre original
    if not os.path.exists(output_file):
        matches = list(Path(OUTPUT_DIR).glob(f"processed_*{job_id}*"))
        if not matches:
            return jsonify({"error": "File not found"}), 404
        output_file = str(matches[0])

    return send_file(output_file, as_attachment=True)


@app.route("/clear", methods=["POST"])
def clear():
    for f in Path(INPUT_DIR).glob("*"):
        f.unlink()
    for f in Path(OUTPUT_DIR).glob("*"):
        f.unlink()
    with queue_lock:
        job_queue.clear()
        jobs.clear()
    return jsonify({"message": "Cleared"}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
