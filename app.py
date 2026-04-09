"""
Simple HTTP API for the video processor.
Allows triggering batch processing via web requests.
"""

from flask import Flask, request, jsonify
import subprocess
import os
import threading
from pathlib import Path

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
    input_files = list(Path(INPUT_DIR).glob("*.mp4")) + list(Path(INPUT_DIR).glob("*.mov")) if Path(INPUT_DIR).exists() else []
    output_files = list(Path(OUTPUT_DIR).glob("*.mp4")) if Path(OUTPUT_DIR).exists() else []
    return jsonify({
        "status": "online",
        "input_videos": len(input_files),
        "output_videos": len(output_files),
        "processor_running": processing_status["running"]
    })


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


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
