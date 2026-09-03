from fastapi import APIRouter, File, UploadFile
import os


router = APIRouter()


UPLOAD_DIR = "upload_files"
os.makedirs(UPLOAD_DIR, exist_ok=True )

@router.post("/files/upload")
def get_files(file: UploadFile=File(...)):
     file_location = os.path.join(UPLOAD_DIR, file.filename)
     with open(file_location, "wb") as buffer:
          buffer.write(file.file.read())

     return {"filename": f"{file.filename} успешно загружен"}
