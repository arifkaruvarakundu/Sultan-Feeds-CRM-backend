from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text
from langchain_community.utilities import SQLDatabase
from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.agents.agent_toolkits.sql.prompt import SQL_PREFIX
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
import re

load_dotenv()
router = APIRouter()

# Load secrets
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

CUSTOM_SCHEMA = {
    "orders": """
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    external_id BIGINT,
    order_key TEXT,
    customer_id INTEGER,
    status TEXT,
    total_amount FLOAT,
    created_at TIMESTAMP,
    payment_method TEXT,
    attribution_referrer TEXT,
    session_pages INTEGER,
    session_count INTEGER,
    device_type TEXT
);
""",
    "order_items": """
CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER,
    product_id BIGINT,
    product_name TEXT,
    quantity INTEGER,
    price FLOAT
);
""",
    "customers": """
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT
);
""",
    "products": """
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    external_id BIGINT,
    name TEXT,
    short_description TEXT,
    regular_price FLOAT,
    sales_price FLOAT,
    total_sales INTEGER,
    categories TEXT,
    stock_status TEXT,
    weight FLOAT,
    date_created TIMESTAMP,
    date_modified TIMESTAMP
);
"""
}

# Set up LangChain SQL agent
# db = SQLDatabase.from_uri(
#     DATABASE_URL,
#     include_tables=["orders", "order_items", "customers", "products"],
#     custom_table_info=CUSTOM_SCHEMA,
#     sample_rows_in_table_info=3 # optional, gives LLM better context
# )
llm = ChatGroq(temperature=0, model_name="compound-beta-mini", api_key=GROQ_API_KEY)

examples_text = """
# Question: Total amount of last 7 orders
# SQL:
SELECT SUM(total_amount)
FROM (
  SELECT total_amount FROM orders
  ORDER BY created_at DESC
  LIMIT 7
) AS last_n_orders;

# Question: How many orders in the last 7 days?
# SQL:
SELECT COUNT(*) FROM orders
WHERE created_at >= NOW() - INTERVAL '7 days';

# Question: Show last 5 orders
# SQL:
SELECT * FROM orders
ORDER BY created_at DESC
LIMIT 5;

# Question: Who are the top 5 customers by spend?
# SQL:
SELECT c.first_name, c.last_name, SUM(o.total_amount) AS total_spent
FROM customers c
JOIN orders o ON o.customer_id = c.id
GROUP BY c.id
ORDER BY total_spent DESC
LIMIT 5;

# Question: Which customers ordered most?
# SQL:
SELECT c.first_name, c.last_name, COUNT(o.id) AS order_count
FROM customers c
JOIN orders o ON o.customer_id = c.id
GROUP BY c.id
ORDER BY order_count DESC;

# Question: Top 10 selling products
# SQL:
SELECT p.name, SUM(oi.quantity) AS total_sold
FROM order_items oi
JOIN products p ON oi.product_id = p.external_id
GROUP BY p.id
ORDER BY total_sold DESC
LIMIT 10;

# Question: How much revenue per product?
# SQL:
SELECT p.name, SUM(oi.price * oi.quantity) AS revenue
FROM order_items oi
JOIN products p ON oi.product_id = p.external_id
GROUP BY p.id;

# Question: Orders by device type
# SQL:
SELECT device_type, COUNT(*) AS total_orders
FROM orders
GROUP BY device_type;

# Question: How many orders from Instagram?
# SQL:
SELECT COUNT(*) FROM orders
WHERE attribution_referrer ILIKE '%instagram%';

# Question: Which customers are from California?
# SQL:
SELECT c.first_name, c.last_name, a.city, a.state
FROM customers c
JOIN addresses a ON a.customer_id = c.id
WHERE a.state ILIKE '%california%' OR a.city ILIKE '%california%';

# Question: Which customers are from Amman?
# SQL:
SELECT c.first_name, c.last_name, a.city
FROM customers c
JOIN addresses a ON a.customer_id = c.id
WHERE a.city ILIKE '%amman%';


# Question: List all orders with customer and product names
# SQL:
SELECT o.id AS order_id, o.created_at, c.first_name, c.last_name,
       oi.product_name, oi.quantity, oi.price
FROM orders o
JOIN customers c ON o.customer_id = c.id
JOIN order_items oi ON oi.order_id = o.id
ORDER BY o.created_at DESC;
"""

CUSTOM_SQL_PREFIX = SQL_PREFIX + "\n\n" + examples_text + """

IMPORTANT NOTES for the database:
- The 'orders' table uses 'created_at' (NOT 'order_date') for timestamps.
- The 'orders' table uses 'total_amount' (NOT 'total') for monetary value.
- To count recent orders, use `created_at >= NOW() - INTERVAL 'X days'`
- The relationship between 'orders' and 'customers' is through 'customer_id'.
- The 'order_items' table links 'orders' and 'products' via 'order_id' and 'product_id'.
- Product sales should be calculated from 'order_items' by joining with 'products'.
- Use 'price * quantity' to compute total sales per product from 'order_items'.
"""

# CUSTOM_SQL_PREFIX = SQL_PREFIX + """

# IMPORTANT NOTES for the database:

# - The 'orders' table uses 'created_at' (NOT 'order_date') for timestamps.
# - The 'orders' table uses 'total_amount' (NOT 'total') for monetary value.
# - To count recent orders, use `created_at >= NOW() - INTERVAL 'X days'`
# - The relationship between 'orders' and 'customers' is through 'customer_id'.
# - The 'order_items' table links 'orders' and 'products' via 'order_id' and 'product_id'.
# - Product sales should be calculated from 'order_items' by joining with 'products'.
# - Use 'price * quantity' to compute total sales per product from 'order_items'.
# """
agent_executor = create_sql_agent(
    llm=llm,
    toolkit=SQLDatabaseToolkit(db=db, llm=llm),
    agent_type="zero-shot-react-description",
    handle_parsing_errors=True,
    verbose=True,
    prefix=CUSTOM_SQL_PREFIX
)

class QueryRequest(BaseModel):
    question: str

def ensure_joins(sql: str) -> str:
    """
    Ensures SQL joins use the correct keys across known table relationships.
    Also adds missing FROM clauses when required.
    """
    
    # Known correct joins (wrong_pattern -> correct_sql_fragment)
    join_fixes = [
        # Products should be joined on external_id
        (r"JOIN\s+products\s+p?\s*ON\s+order_items\.product_id\s*=\s*products\.id", 
         "JOIN products ON order_items.product_id = products.external_id"),
        
        # Orders -> Order Items
        (r"JOIN\s+order_items\s+oi?\s*ON\s+orders\.id\s*=\s*order_items\.order_id", 
         "JOIN order_items ON orders.id = order_items.order_id"),
        
        # Customers -> Orders
        (r"JOIN\s+orders\s+o?\s*ON\s+customers\.id\s*=\s*orders\.customer_id", 
         "JOIN orders ON orders.customer_id = customers.id"),
        
        # Orders -> Customers
        (r"JOIN\s+customers\s+c?\s*ON\s+orders\.customer_id\s*=\s*customers\.id", 
         "JOIN customers ON orders.customer_id = customers.id"),

        # Customers -> Addresses (even if address table is not defined in schema, prepare for it)
        (r"JOIN\s+addresses\s+a?\s*ON\s+customers\.id\s*=\s*addresses\.customer_id", 
         "JOIN addresses ON addresses.customer_id = customers.id"),
    ]

    # Apply all join fixes
    for wrong_pattern, correct_join in join_fixes:
        sql = re.sub(wrong_pattern, correct_join, sql, flags=re.IGNORECASE)

    # Check presence of table references
    sql_lower = sql.lower()
    present_tables = set(re.findall(r"(from|join)\s+([a-z_]+)", sql_lower))
    present_table_names = {table for _, table in present_tables}

    # Heuristic: Add missing FROM clause if needed
    if "from" not in sql_lower:
        for table in ["orders", "order_items", "customers", "products"]:
            if table in sql_lower:
                sql = f"FROM {table} " + sql
                break

    # Add inferred joins (if a field is used but no join exists)
    if "products." in sql and "products" not in present_table_names:
        if "order_items" in present_table_names:
            sql += " JOIN products ON order_items.product_id = products.external_id"
        else:
            sql += " JOIN order_items ON orders.id = order_items.order_id"
            sql += " JOIN products ON order_items.product_id = products.external_id"
        present_table_names.update(["order_items", "products"])

    if "order_items." in sql and "order_items" not in present_table_names:
        if "orders" in present_table_names:
            sql += " JOIN order_items ON orders.id = order_items.order_id"
        else:
            sql += " FROM order_items"
        present_table_names.add("order_items")

    if "customers." in sql and "customers" not in present_table_names:
        if "orders" in present_table_names:
            sql += " JOIN customers ON orders.customer_id = customers.id"
        else:
            sql += " FROM customers"
        present_table_names.add("customers")

    if "orders." in sql and "orders" not in present_table_names:
        if "order_items" in present_table_names:
            sql += " JOIN orders ON orders.id = order_items.order_id"
        elif "customers" in present_table_names:
            sql += " JOIN orders ON orders.customer_id = customers.id"
        else:
            sql += " FROM orders"
        present_table_names.add("orders")

    if "addresses." in sql and "addresses" not in present_table_names:
        sql += " JOIN addresses ON addresses.customer_id = customers.id"
        present_table_names.add("addresses")

    return sql

def fix_sql_aliases(sql: str) -> str:
    # Check if aliases are defined
    has_oi = re.search(r"\border_items\s+oi\b", sql, re.IGNORECASE)
    has_p = re.search(r"\bproducts\s+p\b", sql, re.IGNORECASE)
    has_o = re.search(r"\borders\s+o\b", sql, re.IGNORECASE)
    has_c = re.search(r"\bcustomers\s+c\b", sql, re.IGNORECASE)

    replacements = {}
    if not has_p:
        replacements[r"\bp\."] = "products."
    if not has_oi:
        replacements[r"\boi\."] = "order_items."
    if not has_o:
        replacements[r"\bo\."] = "orders."
    if not has_c:
        replacements[r"\bc\."] = "customers."

    for pattern, replacement in replacements.items():
        sql = re.sub(pattern, replacement, sql)

    return sql

@router.post("/ask-ai")
async def ask_ai(req: QueryRequest):
    try:
        result = agent_executor.invoke({"input": req.question})
    except Exception as e:
        error_msg = str(e)
        if "Action Input:" in error_msg:
            import re
            match = re.search(r"Action Input:\s*(SELECT.*?)(?:\n|$)", error_msg, re.DOTALL | re.IGNORECASE)
            if match:
                raw_sql = match.group(1).strip().rstrip(";")
                fixed_sql = ensure_joins(fix_sql_aliases(raw_sql))
                try:
                    with db._engine.connect() as conn:
                        print("✅ Executing SQL:", fixed_sql)
                        result_proxy = conn.execute(text(fixed_sql))
                        rows = result_proxy.fetchall()
                        keys = result_proxy.keys()
                        formatted_result = [dict(zip(keys, row)) for row in rows]
                    return {
                        "question": req.question,
                        "sql_query": fixed_sql,
                        "result": formatted_result
                    }
                except Exception as inner_db_error:
                    return {"error": f"SQL Execution Failed: {str(inner_db_error)}"}
        return {"error": "Agent failed and no SQL could be extracted", "details": error_msg}

    # Normal flow: extract SQL, fix aliases, execute
    intermediate_steps = result.get("intermediate_steps", [])
    sql_query = None

    for step in intermediate_steps:
        action, _ = step
        if action.tool == "sql_db_query":
            sql_query = action.tool_input.strip()
            break

    if sql_query:
        fixed_sql = ensure_joins(fix_sql_aliases(sql_query))
        # Basic SQL validation
        if "from" not in fixed_sql.lower():
            return {
                "error": "Generated SQL is incomplete — missing FROM clause.",
                "raw_sql": sql_query,
                "question": req.question
            }

        with db._engine.connect() as conn:
            result_proxy = conn.execute(text(fixed_sql))
            rows = result_proxy.fetchall()
            keys = result_proxy.keys()
            formatted_result = [dict(zip(keys, row)) for row in rows]

        return {
            "question": req.question,
            "sql_query": fixed_sql,
            "result": formatted_result
        }

    return {"answer": result.get("output", "No answer generated")}