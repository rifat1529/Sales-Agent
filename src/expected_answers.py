"""Independent answer key: direct SQL against SQLite, never through the agent tools."""
import sqlite3
from .config import DB_PATH

QUESTIONS = [
    {"id": "Q01", "question": "How many customers are there?", "kind": "number", "sql": "SELECT COUNT(*) FROM customers"},
    {"id": "Q02", "question": "How many products are in the catalog?", "kind": "number", "sql": "SELECT COUNT(*) FROM products"},
    {"id": "Q03", "question": "How many orders are recorded?", "kind": "number", "sql": "SELECT COUNT(*) FROM orders"},
    {"id": "Q04", "question": "How many order item rows are recorded?", "kind": "number", "sql": "SELECT COUNT(*) FROM order_items"},
    {"id": "Q05", "question": "What is the total revenue from completed orders?", "kind": "number", "sql": "SELECT ROUND(SUM(oi.quantity*oi.unit_price*(1-oi.discount_pct/100.0)),2) FROM order_items oi JOIN orders o ON o.order_id=oi.order_id WHERE o.status='completed'"},
    {"id": "Q06", "question": "What is the total revenue for customer 12 across completed orders?", "kind": "number", "sql": "SELECT ROUND(SUM(oi.quantity*oi.unit_price*(1-oi.discount_pct/100.0)),2) FROM orders o JOIN order_items oi ON oi.order_id=o.order_id WHERE o.customer_id=12 AND o.status='completed'"},
    {"id": "Q07", "question": "How many orders does customer 25 have?", "kind": "number", "sql": "SELECT COUNT(*) FROM orders WHERE customer_id=25"},
    {"id": "Q08", "question": "Which product category earned the most revenue from completed orders?", "kind": "text", "sql": "SELECT p.category FROM order_items oi JOIN products p ON p.product_id=oi.product_id JOIN orders o ON o.order_id=oi.order_id WHERE o.status='completed' GROUP BY p.category ORDER BY SUM(oi.quantity*oi.unit_price*(1-oi.discount_pct/100.0)) DESC LIMIT 1"},
    {"id": "Q09", "question": "What is the average order value for completed orders?", "kind": "number", "sql": "SELECT ROUND(AVG(order_total),2) FROM (SELECT o.order_id,SUM(oi.quantity*oi.unit_price*(1-oi.discount_pct/100.0)) order_total FROM orders o JOIN order_items oi ON oi.order_id=o.order_id WHERE o.status='completed' GROUP BY o.order_id)"},
    {"id": "Q10", "question": "What is the minimum completed order value?", "kind": "number", "sql": "SELECT ROUND(MIN(order_total),2) FROM (SELECT o.order_id,SUM(oi.quantity*oi.unit_price*(1-oi.discount_pct/100.0)) order_total FROM orders o JOIN order_items oi ON oi.order_id=o.order_id WHERE o.status='completed' GROUP BY o.order_id)"},
    {"id": "Q11", "question": "What percent is the average completed order value above the minimum completed order value?", "kind": "number", "sql": "WITH totals AS (SELECT o.order_id,SUM(oi.quantity*oi.unit_price*(1-oi.discount_pct/100.0)) v FROM orders o JOIN order_items oi ON oi.order_id=o.order_id WHERE o.status='completed' GROUP BY o.order_id) SELECT ROUND((AVG(v)-MIN(v))*100.0/MIN(v),2) FROM totals"},
    {"id": "Q12", "question": "What is the difference between the number of completed and cancelled orders?", "kind": "number", "sql": "SELECT (SELECT COUNT(*) FROM orders WHERE status='completed')-(SELECT COUNT(*) FROM orders WHERE status='cancelled')"},
    {"id": "Q13", "question": "Which city has the most customers?", "kind": "text", "sql": "SELECT city FROM customers GROUP BY city ORDER BY COUNT(*) DESC, city LIMIT 1"},
    {"id": "Q14", "question": "What is the total quantity of Electronics products sold in completed orders?", "kind": "number", "sql": "SELECT SUM(oi.quantity) FROM order_items oi JOIN products p ON p.product_id=oi.product_id JOIN orders o ON o.order_id=oi.order_id WHERE p.category='Electronics' AND o.status='completed'"},
    {"id": "Q15", "question": "What is the revenue growth percentage from the first half to the second half of 2025 for completed orders?", "kind": "number", "sql": "WITH h AS (SELECT CASE WHEN CAST(substr(o.order_date,6,2) AS INTEGER)<=6 THEN 'H1' ELSE 'H2' END half,SUM(oi.quantity*oi.unit_price*(1-oi.discount_pct/100.0)) revenue FROM orders o JOIN order_items oi ON oi.order_id=o.order_id WHERE o.status='completed' GROUP BY half) SELECT ROUND((MAX(CASE WHEN half='H2' THEN revenue END)-MAX(CASE WHEN half='H1' THEN revenue END))*100.0/MAX(CASE WHEN half='H1' THEN revenue END),2) FROM h"},
    {"id": "Q16", "question": "What is the total revenue for customer 12 and how many completed orders did they place?", "kind": "multi", "sql": "SELECT ROUND(SUM(oi.quantity*oi.unit_price*(1-oi.discount_pct/100.0)),2),COUNT(DISTINCT o.order_id) FROM orders o JOIN order_items oi ON oi.order_id=o.order_id WHERE o.customer_id=12 AND o.status='completed'"},
    {"id": "Q17", "question": "What was the revenue in Dhaka during the first quarter of 2025, and how many distinct customers contributed?", "kind": "multi", "sql": "SELECT ROUND(SUM(oi.quantity*oi.unit_price*(1-oi.discount_pct/100.0)),2),COUNT(DISTINCT o.customer_id) FROM orders o JOIN customers c ON c.customer_id=o.customer_id JOIN order_items oi ON oi.order_id=o.order_id WHERE c.city='Dhaka' AND o.status='completed' AND o.order_date>='2025-01-01' AND o.order_date<'2025-04-01'"},
    {"id": "Q18", "question": "What is each customer's lifetime value in the year 2035?", "kind": "unanswerable", "sql": None},
    {"id": "Q19", "question": "How many customers have a verified email address?", "kind": "unanswerable", "sql": None},
]

def compute_expected(db_path=DB_PATH):
    con = sqlite3.connect(db_path)
    try:
        answers = {}
        for item in QUESTIONS:
            if item["kind"] == "unanswerable":
                answers[item["id"]] = None
            else:
                row = con.execute(item["sql"]).fetchone()
                answers[item["id"]] = list(row) if len(row) > 1 else row[0]
        return answers
    finally:
        con.close()

if __name__ == "__main__":
    import json
    print(json.dumps(compute_expected(), indent=2))
