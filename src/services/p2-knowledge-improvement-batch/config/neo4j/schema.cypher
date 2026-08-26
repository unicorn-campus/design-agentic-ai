CREATE CONSTRAINT customer_key IF NOT EXISTS FOR (n:고객) REQUIRE n.customer_ref IS NODE KEY;
CREATE CONSTRAINT card_key IF NOT EXISTS FOR (n:카드) REQUIRE n.card_ref IS NODE KEY;
CREATE CONSTRAINT product_key IF NOT EXISTS FOR (n:상품) REQUIRE n.product_code IS NODE KEY;
CREATE CONSTRAINT transaction_key IF NOT EXISTS FOR (n:거래) REQUIRE n.transaction_ref IS NODE KEY;
CREATE CONSTRAINT consultation_key IF NOT EXISTS FOR (n:문의) REQUIRE n.consultation_ref IS NODE KEY;
CREATE CONSTRAINT dispute_key IF NOT EXISTS FOR (n:분쟁) REQUIRE n.dispute_ref IS NODE KEY;
CREATE RANGE INDEX consultation_topic IF NOT EXISTS FOR (n:문의) ON (n.topic_code);
CREATE FULLTEXT INDEX product_name IF NOT EXISTS FOR (n:상품) ON EACH [n.product_name];
