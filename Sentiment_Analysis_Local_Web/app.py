# app.py (full, modified)
import traceback
import json
import os

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse

import inference
import csv_nlp
import runtime
import topic_summary
import excel_pipeline

import ui_shell
import ui_home
import ui_single
import ui_csv
import ui_script


APP_HTML = (
    ui_shell.HTML_PREFIX
    + ui_home.VIEW_HOME
    + ui_single.VIEW_SINGLE
    + ui_csv.VIEW_CSV
    + ui_shell.HTML_BEFORE_SCRIPT
    + ui_script.JS
    + ui_shell.HTML_SUFFIX
)

app = FastAPI()


@app.exception_handler(Exception)
async def any_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": repr(exc), "traceback": traceback.format_exc()},
    )


@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(APP_HTML)


@app.get("/single", response_class=HTMLResponse)
def single():
    return HTMLResponse(APP_HTML)


@app.get("/csv", response_class=HTMLResponse)
def csv_page():
    return HTMLResponse(APP_HTML)


@app.get("/api/vram")
def api_vram():
    return JSONResponse(status_code=200, content=runtime.get_vram_status())


@app.post("/api/excel_clean_gibberish_stream")
async def api_excel_clean_gibberish_stream(
    file: UploadFile = File(...),
):
    filename = str(file.filename or "uploaded.csv")
    if not filename.lower().endswith((".csv", ".xlsx", ".xlsm")):
        return JSONResponse(
            status_code=400,
            content={"detail": "Please upload a table file (.csv/.xlsx/.xlsm)."},
        )

    raw = await file.read()
    if not raw:
        return JSONResponse(status_code=400, content={"detail": "Uploaded file is empty."})

    if not excel_pipeline.try_acquire_job():
        return JSONResponse(
            status_code=409,
            content={"detail": "Another table job is running. Please wait and retry."},
        )

    def event_iter():
        try:
            for ev in excel_pipeline.iter_excel_cleaning_and_gibberish(raw, filename):
                yield "data: " + json.dumps(ev, ensure_ascii=False) + "\n\n"
        except Exception as e:
            err = {"type": "error", "detail": repr(e)}
            yield "data: " + json.dumps(err, ensure_ascii=False) + "\n\n"
        finally:
            excel_pipeline.release_job()

    return StreamingResponse(event_iter(), media_type="text/event-stream")


@app.get("/api/excel_download/{job_id}")
def api_excel_download(job_id: str):
    meta = excel_pipeline.get_output_file(job_id)
    if not meta:
        return JSONResponse(status_code=404, content={"detail": "Output file not found."})

    path = str(meta.get("path", ""))
    filename = str(meta.get("filename", "processed_table.csv"))
    if not path or (not os.path.exists(path)):
        return JSONResponse(status_code=404, content={"detail": "Output file expired or missing."})

    fn_lower = filename.lower()
    if fn_lower.endswith(".csv"):
        media_type = "text/csv; charset=utf-8"
    else:
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return FileResponse(
        path=path,
        filename=filename,
        media_type=media_type,
    )


@app.post("/api/analyse")
async def api_analyse(request: Request):
    payload = await request.json()
    text = str(payload.get("text", "")).strip()

    raw = ""
    try:
        pred, conf, raw = inference.infer_sentiment(text)
        if pred == "Unknown":
            return JSONResponse(
                status_code=500,
                content={"detail": "Could not parse Sentiment_Classification output.", "raw": raw},
            )

        return JSONResponse(status_code=200, content={"prediction": pred, "confidence": conf})
    finally:
        runtime.unload_sentiment_model()


@app.post("/api/summary_stream")
async def api_summary_stream(request: Request):
    payload = await request.json()
    _ = str(payload.get("text", "")).strip()

    def event_iter():
        yield inference.sse_pack_text_piece("Summarisation is not enabled yet.")
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_iter(), media_type="text/event-stream")


@app.post("/api/topic_summary_stream")
async def api_topic_summary_stream(request: Request):
    payload = await request.json()
    topic_id = str(payload.get("topic_id", "")).strip()
    cls = str(payload.get("cls", "Positive")).strip() or "Positive"

    if not topic_id:
        return JSONResponse(status_code=400, content={"detail": "Missing topic_id"})

    if not runtime.try_acquire_llama_job():
        return JSONResponse(status_code=409, content={"detail": "LLAMA_BUSY"})

    def event_iter():
        try:
            for ev in topic_summary.iter_topic_summary_sse(topic_id, cls):
                yield ev
        finally:
            runtime.release_llama_job()

    return StreamingResponse(event_iter(), media_type="text/event-stream")


@app.post("/api/csv_analyse_stream")
async def api_csv_analyse_stream(
    file: UploadFile = File(...),
    col_letters: str = Form(...),
):
    raw = await file.read()

    def event_iter():
        try:
            for ev in csv_nlp.iter_csv_analysis(raw, col_letters):
                yield "data: " + json.dumps(ev, ensure_ascii=False) + "\n\n"
        except Exception as e:
            err = {"type": "error", "detail": repr(e)}
            yield "data: " + json.dumps(err, ensure_ascii=False) + "\n\n"

    return StreamingResponse(event_iter(), media_type="text/event-stream")
