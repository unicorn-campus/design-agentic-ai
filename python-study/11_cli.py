""" 
CLI로 파라미터 받아 처리
"""

import argparse
import sqlite3
from datetime import date

from context_builder import build_context

def parse_args():
    parser = argparse.ArgumentParser( description="고객 Context 조회 연습")
    
    parser.add_argument(
        "-m",
        "--member-id",
        default="M-0001"
    )
    
    parser.add_argument(
        "-d",
        "--base-date",
        default=date.today().strftime("%Y-%m-%d")
    )
    
    return parser.parse_args()
    
def validate_date(base_date):
    date.fromisoformat(base_date)

class CustomerContextApp:
    def __init__(self, dbpath):
        self.dbpath = dbpath
    
    def fetch_products(self):
        with sqlite3.connect(self.dbpath) as connection:
            cursor = connection.cursor()
            
            cursor.execute(""" 
              SELECT product_name, annual_fee 
              FROM product
              ORDER BY product_id               
            """)
            
            return cursor.fetchall() 
            
    def load_products(self, rows=None):
        products = []
        
        for name, fee in rows:
            product = { 
                "product_name": name,
                "annual_fee": fee
            }
            products.append(product)
        
        return products    
      
    def make_monthly_usage(self, base_date):
        base_month = base_date[:7]
        
        return [
            { "month": base_month, "total_amount": 1200000 },
            { "month": base_month, "total_amount": 800000  }
        ]
    
    def run(self, member_id, base_date):
        products = self.load_products(self.fetch_products())
        monthly_usage = self.make_monthly_usage(base_date)
        delinquency = None
        
        return build_context(
            member_id,
            base_date,
            products,
            monthly_usage,
            delinquency
        )
    
if __name__ == "__main__":
    args = parse_args()
    
    try:
        validate_date(args.base_date)
    except ValueError:
        print(f"기준일 {args.base_date}은 올바른 날짜 형식이 아닙니다.")
        exit(1)
    
    app = CustomerContextApp("study_cards.sqlite3")
    
    context = app.run(args.member_id, args.base_date)
    
    print(context)
