LOAD CSV WITH HEADERS FROM $customer_file AS row
MERGE (customer:고객 {customer_ref: row.customer_ref})
SET customer.identifier_type = 'HASHED'
MERGE (card:카드 {card_ref: row.card_ref})
MERGE (product:상품 {product_code: row.product_code})
MERGE (transaction:거래 {transaction_ref: row.transaction_ref})
MERGE (customer)-[:보유함]->(card)
MERGE (card)-[:연결상품]->(product)
MERGE (card)-[:발생거래]->(transaction)
FOREACH (_ IN CASE row.disputed WHEN 'true' THEN [1] ELSE [] END |
  MERGE (customer)-[:분쟁제기함]->(transaction)
)
FOREACH (_ IN CASE row.disputed WHEN 'false' THEN [1] ELSE [] END |
  MERGE (customer)-[:분쟁제기하지않음]->(transaction)
)
FOREACH (_ IN CASE WHEN row.dispute_ref IS NOT NULL THEN [1] ELSE [] END |
  MERGE (dispute:분쟁 {dispute_ref: row.dispute_ref})
  MERGE (dispute)-[:대상거래]->(transaction)
);

LOAD CSV WITH HEADERS FROM $consultation_file AS row
MERGE (customer:고객 {customer_ref: row.customer_ref})
SET customer.identifier_type = 'HASHED'
MERGE (consultation:문의 {consultation_ref: row.consultation_ref})
SET consultation.topic_code = row.topic_code,
    consultation.business_date = date(row.business_date)
MERGE (transaction:거래 {transaction_ref: row.transaction_ref})
MERGE (customer)-[:문의함]->(consultation)
MERGE (consultation)-[:대상거래]->(transaction);
