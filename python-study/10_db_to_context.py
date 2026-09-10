import sqlite3

from context_builder import build_context

if __name__ == "__main__":
    with sqlite3.connect("study_cards.sqlite3") as connection:
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT product_name,  annual_fee
            FROM product
            ORDER BY product_id
        """)
        
        rows = cursor.fetchall()
    
    products = []
    for name, fee in rows:
        product = { 
            "product_name": name,
            "annual_fee": fee
        }
        products.append(product)
        
    monthly_usage = [
        { "month": "2026-08", "total_amount": 1200000 },
        { "month": "2026-07", "total_amount": 800000 }
    ]
    
    delinquency = None
    
    context = build_context(
        "M-1002",
        "2026-08-31",
        products,
        monthly_usage,
        delinquency
    )
    
    print(context)