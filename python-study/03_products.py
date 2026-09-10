"""
list와 dictinary를 활용하여 상품 정보를 출력하는 예제입니다.
"""

products = [
  {
    "product_name": "생활 카드",
    "annual_fee": 12000
  },
  {
    "product_name": "여행 카드",
    "annual_fee": 80000
  }
]

for product in products:
    name = product["product_name"]
    fee = product["annual_fee"]
    print(f"상품명: {name}, 연회비: {fee:,}원")
    