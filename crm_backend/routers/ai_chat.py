# from fastapi import APIRouter
# from pydantic import BaseModel
# from langchain_community.utilities import SQLDatabase
# from langchain.chains import create_sql_query_chain
# from langchain_groq import ChatGroq
# import os

# router = APIRouter()

# # Set your Groq API key
# os.environ["GROQ_API_KEY"] = "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"

# # Connect to your database
# db = SQLDatabase.from_uri("postgresql://postgres:harif313@postgres_db:5432/crm_db")

# # Use Mistral model via Groq (supports natural language to SQL generation)
# llm = ChatGroq(temperature=0, model_name="compound-beta-mini")

# # Create a lightweight SQL query chain instead of an agent
# db_chain = create_sql_query_chain(llm=llm, db=db)

# # Request schema
# class QueryRequest(BaseModel):
#     question: str

# # FastAPI route
# @router.post("/ask-ai")
# async def ask_ai(req: QueryRequest):
#     try:
#         result = db_chain.invoke({"question": req.question})
#         return {"answer": result}
#     except Exception as e:
#         return {"error": str(e)}

from fastapi import APIRouter
from pydantic import BaseModel
from langchain_community.utilities import SQLDatabase
from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain_groq import ChatGroq
import os

router = APIRouter()

os.environ["GROQ_API_KEY"] = "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"

# Connect to DB
db = SQLDatabase.from_uri("postgresql://postgres:harif313@postgres_db:5432/crm_db")

# Load LLM
llm = ChatGroq(temperature=0, model_name="compound-beta-mini")

# Create agent that actually executes SQL
agent_executor = create_sql_agent(
    llm=llm,
    toolkit=SQLDatabaseToolkit(db=db, llm=llm),
    verbose=True,
    agent_type="zero-shot-react-description",
    handle_parsing_errors=True
)

class QueryRequest(BaseModel):
    question: str

@router.post("/ask-ai")
async def ask_ai(req: QueryRequest):
    try:
        result = agent_executor.invoke({"input": req.question})
        return {"answer": result["output"]}
    except Exception as e:
        return {"error": str(e)}
