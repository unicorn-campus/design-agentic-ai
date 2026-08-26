CREATE ROLE helpdesk_w1_graph_reader IF NOT EXISTS;
CREATE ROLE helpdesk_w2_graph_reader IF NOT EXISTS;

GRANT TRAVERSE ON GRAPH neo4j NODES 고객 WHERE identifier_type = 'HASHED'
TO helpdesk_w1_graph_reader;
GRANT TRAVERSE ON GRAPH neo4j NODES 카드, 상품, 거래, 문의, 분쟁
TO helpdesk_w1_graph_reader;
GRANT TRAVERSE ON GRAPH neo4j RELATIONSHIPS 보유함, 연결상품, 발생거래, 문의함,
대상거래, 분쟁제기함, 분쟁제기하지않음 TO helpdesk_w1_graph_reader;
GRANT READ {*} ON GRAPH neo4j ELEMENTS 고객, 카드, 상품, 거래, 문의, 분쟁,
보유함, 연결상품, 발생거래, 문의함, 대상거래, 분쟁제기함, 분쟁제기하지않음
TO helpdesk_w1_graph_reader;

GRANT TRAVERSE ON GRAPH neo4j NODES 고객 WHERE identifier_type = 'HASHED'
TO helpdesk_w2_graph_reader;
GRANT TRAVERSE ON GRAPH neo4j NODES 카드, 상품, 거래, 문의, 분쟁
TO helpdesk_w2_graph_reader;
GRANT TRAVERSE ON GRAPH neo4j RELATIONSHIPS 보유함, 연결상품, 발생거래, 문의함,
대상거래, 분쟁제기함, 분쟁제기하지않음 TO helpdesk_w2_graph_reader;
GRANT READ {*} ON GRAPH neo4j ELEMENTS 고객, 카드, 상품, 거래, 문의, 분쟁,
보유함, 연결상품, 발생거래, 문의함, 대상거래, 분쟁제기함, 분쟁제기하지않음
TO helpdesk_w2_graph_reader;
