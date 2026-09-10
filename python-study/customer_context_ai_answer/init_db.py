import sqlite3

if __name__ == "__main__":
    products = [
        ("P001", "생활카드", 12000),
        ("P002", "여행카드", 80000)
    ]
    
    with sqlite3.connect("study_cards.sqlite3") as connection:
        cursor = connection.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product (
                product_id TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                annual_fee INTEGER NOT NULL              
            )           
        """)
        
        cursor.execute("DELETE FROM product")
        
        cursor.executemany(
            """
            INSERT INTO product (
                product_id,
                product_name,
                annual_fee              
            )
            VALUES (?, ?, ?)
            """,
            products
        )
        
        minimum_fee = 50000
        
        cursor.execute(
            """
            select product_name, annual_fee
            FROM product
            WHERE annual_fee >= ?
            ORDER BY annual_fee
            """,
            (minimum_fee,)
        )
        
        rows = cursor.fetchall()
        
        for name, fee in rows:
            print(f"{name}: 연회비 {fee:,}월")
        
        