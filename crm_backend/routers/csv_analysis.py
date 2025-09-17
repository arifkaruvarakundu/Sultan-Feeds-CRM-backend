import os
import io
from openai import OpenAI
import base64
import pandas as pd
from typing import Optional
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi import status
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from langchain_groq import ChatGroq
import matplotlib.pyplot as plt
from crm_backend.AI.csv_analysis import analyze_tabular_bytes, invoke_llm, json_sanitize


load_dotenv()
router = APIRouter()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("GROQ_MODEL", "compound-beta-mini")


# @router.post("/csv/analyze")
# async def analyze_csv(file: UploadFile = File(...), question: Optional[str] = None):
#     if not OPENAI_API_KEY:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="GROQ_API_KEY not set")

#     if not file.filename.lower().endswith((".csv", ".xlsx", ".xls")):
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .csv, .xlsx, .xls files are supported")

#     content_type = (file.content_type or "").lower()
#     allowed_types = {
#         "text/csv",
#         "application/csv",
#         "application/vnd.ms-excel",
#         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         "application/octet-stream",
#     }
#     if content_type and content_type not in allowed_types:
#         # Not fatal, but warn by rejecting to avoid surprises
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported content type: {file.content_type}")

#     try:
#         data = await file.read()
#         _, summary, prompt = analyze_tabular_bytes(
#             data,
#             filename=file.filename,
#             content_type=file.content_type,
#             user_question=question,
#         )
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to parse file: {str(e)}")

#     llm = ChatGroq(temperature=0.2, model_name=MODEL_NAME, api_key=GROQ_API_KEY)
#     analysis = invoke_llm(prompt, llm)

#     return json_sanitize({
#         "filename": file.filename,
#         "summary": summary,
#         "analysis": analysis,
#     })

# @router.post("/analyze/")
# async def analyze_file(file: UploadFile = File(...)):
#     # Validate file type
#     if not file.filename.endswith((".csv", ".xlsx")):
#         return JSONResponse(content={"error": "Invalid file type"}, status_code=400)
    
#     # Read file into pandas
#     contents = await file.read()
#     if file.filename.endswith(".csv"):
#         df = pd.read_csv(io.BytesIO(contents))
#     else:
#         df = pd.read_excel(io.BytesIO(contents))
    
#     # Convert to JSON for OpenAI
#     data_json = df.to_dict(orient="records")
    
#     # Call OpenAI API to analyze
#     prompt = f"Analyze this dataset and provide insights, tables, and visualization suggestions:\n{data_json}"
#     response = openai.ChatCompletion.create(
#         model="gpt-4",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.5
#     )
    
#     # Return response
#     return {"analysis": response.choices[0].message.content}

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
    
    # Summarize dataset (only send preview, not whole file if large)
    preview = df.head(10).to_dict(orient="records")
    summary = {
        "columns": list(df.columns),
        "num_rows": len(df),
        "preview": preview
    }

    # Ask OpenAI for structured output
    prompt = f"""
            Analyze this dataset and output ONLY valid JSON that matches this schema:

            {{
                "analysis": "short text summary of key insights",
                "suggested_tables": [
                    {{
                        "title": "string",
                        "data": [["col1", "col2"], ["val1", "val2"]]
                    }}
                ],
                "suggested_charts": [
                    {{
                        "type": "bar|line|pie",
                        "title": "string",
                        "x": "column name",
                        "y": "column name"
                    }}
                ],
                "recommendations": ["string"]
            }}

            Dataset summary:
            {summary}
            """

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-5",  # or "gpt-3.5-turbo", etc.
        messages=[
            {"role": "system", "content": "You are a data analyst."},
            {"role": "user", "content": prompt}
        ]
    )

    result = response.choices[0].message.content

    # Try parsing LLM response to JSON
    import json
    try:
        structured_output = json.loads(result)
    except json.JSONDecodeError:
        structured_output = {"analysis": result}

    # Generate sample charts from suggestions (if any)
    charts = []
    for chart in structured_output.get("suggested_charts", []):
        try:
            plt.figure()
            if chart["type"] == "bar":
                df.groupby(chart["x"])[chart["y"]].mean().plot(kind="bar")
            elif chart["type"] == "line":
                df.plot(x=chart["x"], y=chart["y"], kind="line")
            elif chart["type"] == "pie":
                df[chart["y"]].value_counts().plot.pie(autopct='%1.1f%%')

            plt.title(chart["title"])
            buf = io.BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            charts.append({
                "title": chart["title"],
                "image_base64": base64.b64encode(buf.read()).decode("utf-8")
            })
            plt.close()
        except Exception as e:
            charts.append({"error": str(e), "chart_request": chart})

    # Return structured response
    return {
        "analysis": structured_output.get("analysis", ""),
        "suggested_tables": structured_output.get("suggested_tables", []),
        "suggested_charts": charts,
        "recommendations": structured_output.get("recommendations", [])
    }




