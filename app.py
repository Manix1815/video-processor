from flask import Flask, request, jsonify, send_file
import subprocess
import os
import threading
import uuid
import time
import json
from pathlib import Path
from collections import deque

app = Flask(__name__)

INPUT_DIR = os.getenv("INPUT_DIR", "/app/data/input")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/app/data/output")
JOBS_FILE = "/app/data/jobs.json"

queue_lock = threading.Lock()
job_queue = deque()
is_processing = False


def load_jobs():
    if os.path.exists(JOBS_FILE):
        with open(JOBS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_jobs(jobs):
    Path(JOBS_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(JOBS_FILE, "w") as f:
        json.dump(jobs, f)


def process_worker():
    global is_processing
    while True:
        job_id = None
        jobs = load_jobs()

        for jid, job in jobs.items():
            if job["status"] == "queued":
                job_id = jid
                break

        if job_id is None:
            time.sleep(5)
            continue

        jobs[job_id]["status"] = "processing"
        save_jobs(jobs)
        is_processing = True

        input_path = jobs[job_id]["input_path"]

        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["python3", "process.py", "--file", input_path, "--output", OUTPUT_DIR],
            capture_output=True, text=True
        )

        jobs = load_jobs()
        if result.returncode == 0:
            matches = list(Path(OUTPUT_DIR).glob("processed_*"))
            if matches:
                latest = max(matches, key=os.path.getctime)
                jobs[job_id]["status"] = "done"
                jobs[job_id]["output_path"] = str(latest)
            else:
                jobs[job_id]["status"] = "error"
                jobs[job_id]["error"] = "Output file not found"
        else:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = result.stderr[-300:]

        save_jobs(jobs)
        is_processing = False

        try:
            os.remove(input_path)
        except:
            pass


worker_thread = threading.Thread(target=process_worker, daemon=True)
worker_thread.start()


@app.route("/", methods=["GET"])
def index():
    jobs = load_jobs()
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

    jobs = load_jobs()
    jobs[job_id] = {
        "status": "queued",
        "input_path": input_path,
        "output_path": None,
        "created_at": time.time()
    }
    save_jobs(jobs)

    return jsonify({
        "job_id": job_id,
        "status": "queued",
        "position": len([j for j in jobs.values() if j["status"] == "queued"])
    }), 200


@app.route("/job/<job_id>", methods=["GET"])
def job_status(job_id):
    jobs = load_jobs()
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    job = jobs[job_id]
    return jsonify({
        "job_id": job_id,
        "status": job["status"]
    })


@app.route("/download/<job_id>", methods=["GET"])
def download(job_id):
    jobs = load_jobs()
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404

    job = jobs[job_id]
    if job["status"] != "done":
        return jsonify({"error": "Not ready", "status": job["status"]}), 425

    output_file = job.get("output_path")
    if not output_file or not os.path.exists(output_file):
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
    if os.path.exists(JOBS_FILE):
        os.remove(JOBS_FILE)
    return jsonify({"message": "Cleared"}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
