from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse  
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import shutil
import os
import pytesseract
from PIL import Image
import pdfplumber
from pdf2image import convert_from_path  # For scanned PDF OCR fallback


app = FastAPI()

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(SessionMiddleware, secret_key="super-secret-key")


def extract_text_from_pdf(file_path):
    """
    Try pdfplumber first (works for text-based PDFs).
    If blank, fall back to OCR (works for scanned/image PDFs).
    """
    extracted_text = ""

    # Step 1: Try pdfplumber for text-based PDFs
    with pdfplumber.open(file_path) as pdf:
        pages_text = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
        extracted_text = "\n".join(pages_text).strip()

    # Step 2: If no text found, it's a scanned PDF — use OCR
    if not extracted_text:
        print("No text found via pdfplumber, falling back to OCR...")
        images = convert_from_path(file_path, dpi=300)
        ocr_texts = []
        for image in images:
            text = pytesseract.image_to_string(image)
            if text.strip():
                ocr_texts.append(text)
        extracted_text = "\n".join(ocr_texts).strip()

    return extracted_text


@app.post("/upload", response_class=HTMLResponse)
async def upload_file(request: Request, file: UploadFile = File(...)):

    allowed_types = ["image/png", "image/jpeg", "application/pdf"]

    if file.content_type not in allowed_types:
        return HTMLResponse("Invalid file type. Only JPG, PNG, PDF allowed.")

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    extracted_text = ""

    if file.content_type in ["image/png", "image/jpeg"]:
        image = Image.open(file_path)
        extracted_text = pytesseract.image_to_string(image)
        print("Extracted Image Text:", extracted_text)

    elif file.content_type == "application/pdf":
        extracted_text = extract_text_from_pdf(file_path)
        print("Extracted PDF Text:", extracted_text)

    request.session["extracted_text"] = extracted_text

    return templates.TemplateResponse("result.html", {
        "request": request,
        "username": request.session.get("user"),
        "role": request.session.get("role"),
        "extracted_text": extracted_text
    })


# Dummy user data (replace with DB later)
fake_users = {
    "doctor1": {"password": "doc123", "role": "Doctor"},
    "pharma1": {"password": "pharma123", "role": "Pharmacy"},
    "admin1": {"password": "admin123", "role": "Admin"},
}


@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = fake_users.get(username)

    if user and user["password"] == password:
        request.session["user"] = username
        request.session["role"] = user["role"]
        return RedirectResponse("/upload", status_code=303)
    else:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid username or password"
        })


@app.get("/upload", response_class=HTMLResponse)
async def upload(request: Request):
    return templates.TemplateResponse("upload.html", {
        "request": request,
        "username": request.session.get("user"),
        "role": request.session.get("role")
    })


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
