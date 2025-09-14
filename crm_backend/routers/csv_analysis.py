import os
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi import status
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from langchain_groq import ChatGroq
import openai
import pandas as pd
import io

from crm_backend.AI.csv_analysis import analyze_tabular_bytes, invoke_llm, json_sanitize


load_dotenv()
router = APIRouter()


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("GROQ_MODEL", "compound-beta-mini")


@router.post("/csv/analyze")
async def analyze_csv(file: UploadFile = File(...), question: Optional[str] = None):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="GROQ_API_KEY not set")

    if not file.filename.lower().endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .csv, .xlsx, .xls files are supported")

    content_type = (file.content_type or "").lower()
    allowed_types = {
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",
    }
    if content_type and content_type not in allowed_types:
        # Not fatal, but warn by rejecting to avoid surprises
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported content type: {file.content_type}")

    try:
        data = await file.read()
        _, summary, prompt = analyze_tabular_bytes(
            data,
            filename=file.filename,
            content_type=file.content_type,
            user_question=question,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to parse file: {str(e)}")

    llm = ChatGroq(temperature=0.2, model_name=MODEL_NAME, api_key=GROQ_API_KEY)
    analysis = invoke_llm(prompt, llm)

    return json_sanitize({
        "filename": file.filename,
        "summary": summary,
        "analysis": analysis,
    })

@router.post("/analyze/")
async def analyze_file(file: UploadFile = File(...)):
    # Validate file type
    if not file.filename.endswith((".csv", ".xlsx")):
        return JSONResponse(content={"error": "Invalid file type"}, status_code=400)
    
    # Read file into pandas
    contents = await file.read()
    if file.filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(contents))
    else:
        df = pd.read_excel(io.BytesIO(contents))
    
    # Convert to JSON for OpenAI
    data_json = df.to_dict(orient="records")
    
    # Call OpenAI API to analyze
    prompt = f"Analyze this dataset and provide insights, tables, and visualization suggestions:\n{data_json}"
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )
    
    # Return response
    return {"analysis": response.choices[0].message.content}


