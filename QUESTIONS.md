# Evaluation Question Set

There are 19 questions. Expected answers are generated independently by direct SQL in `src/expected_answers.py`; do not manually transcribe results from agent responses.

| ID | Type | Question |
|---|---|---|
| Q01 | Simple | How many customers are there? |
| Q02 | Simple | How many products are in the catalog? |
| Q03 | Simple | How many orders are recorded? |
| Q04 | Simple | How many order item rows are recorded? |
| Q05 | Join / total | What is the total revenue from completed orders? |
| Q06 | Join / customer total | What is the total revenue for customer 12 across completed orders? |
| Q07 | Filter / count | How many orders does customer 25 have? |
| Q08 | Grouping | Which product category earned the most revenue from completed orders? |
| Q09 | Average | What is the average order value for completed orders? |
| Q10 | Minimum | What is the minimum completed order value? |
| Q11 | Percentage | What percent is the average completed order value above the minimum completed order value? |
| Q12 | Difference | What is the difference between the number of completed and cancelled orders? |
| Q13 | Grouping | Which city has the most customers? |
| Q14 | Join / sum | What is the total quantity of Electronics products sold in completed orders? |
| Q15 | Growth | What is the revenue growth percentage from the first half to the second half of 2025 for completed orders? |
| Q16 | Multi-result | What is the total revenue for customer 12 and how many completed orders did they place? |
| Q17 | Multi-result | What was the revenue in Dhaka during the first quarter of 2025, and how many distinct customers contributed? |
| Q18 | Unanswerable | What is each customer's lifetime value in the year 2035? |
| Q19 | Unanswerable | How many customers have a verified email address? |

Run each question three times using `python evaluate.py`. The expected answers are calculated independently by SQL at evaluation time.
