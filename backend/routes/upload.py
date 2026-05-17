from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
import io
try:
    from pypdf import PdfReader
except Exception:
    from PyPDF2 import PdfReader
from services.auth_service import get_current_user
from services.db_service import User
import services.resume_store as store

router = APIRouter()

@router.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    _ = current_user
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a valid PDF resume.")

    try:
        file_bytes = await file.read()
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""

        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Resume text could not be extracted. Please upload a readable PDF.",
            )

        store.resume_text = text
        return {
            "message": "Resume processed successfully", 
            "text": text,
            "length": len(text)
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Unable to parse this PDF. Please try another resume file.",
        )
