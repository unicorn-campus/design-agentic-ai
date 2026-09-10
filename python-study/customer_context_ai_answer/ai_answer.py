import argparse
import os
from datetime import date

from anthropic import Anthropic, APIConnectionError, APIStatusError
from dotenv import load_dotenv
from customer_context_app import CustomerContextApp, validate_date

def parse_args():
    parser = argparse.ArgumentParser(description="고객 컨텍스트 생성기")
    parser.add_argument("-m","--member-id", type=str, default="user1", help="고객 ID")
    parser.add_argument("-d", "--base-date", type=str, default=date.today().strftime("%Y-%m-%d"), help="기준일 (YYYY-MM-DD 형식)")
    parser.add_argument("-q", "--query", default="보유 상품을 요약해 주세요")
    parser.add_argument("--offline", action="store_true", help="오프라인 모드 (AI 모델 호출 없이 컨텍스트만 생성)")
    return parser.parse_args()
  
def build_user_input(question, context):
    return f"""
<question>
{question}
</question>

<context>
{context}
</context>  
"""

class ClaudeGateway:
    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model
    
    def ask(self, system, user):
        if not self.api_key:
            raise ValueError("API 키가 설정되지 않았습니다.")
        
        try:
            client = Anthropic(api_key=self.api_key)
            
            message = client.messages.create(
                model=self.model,
                max_tokens=3000,
                system=system,
                messages=[
                    {
                        "role": "user", 
                        "content": user
                    }
                ]
            )
        except APIStatusError as error:
            raise RuntimeError(f"AI API 호출 실패: HTTP {error.status_code} - {error.message}") from None
        except APIConnectionError:
            raise RuntimeError(f"AI API 연결 실패") from None
        
        texts = []
        
        for block in message.content:
            if block.type == "text":
                texts.append(block.text)
                
        return "".join(texts)
      

if __name__ == "__main__":
    args = parse_args()
    
    try:
        validate_date(args.base_date)
    except ValueError:
        print(f"기준일 형식이 올바르지 않습니다: {args.base_date}")
        exit(1)    
    
    try:
        app = CustomerContextApp("study_cards.sqlite3")
        
        context = app.run(args.member_id, args.base_date)
        
        system = (
            "당신은 금융 전문가입니다. "
            "아래 고객 컨텍스트를 기반으로 고객의 보유 상품을 요약해 주세요."
            "최대한 발랄하고 유머러스한 톤으로 답해줘요."
            "자료가 없으면 '확인필요'라고 표시하세요."
        )
        
        user = build_user_input(args.query, context)
        
        if args.offline:
            print("[SYSTEM]")
            print(system)
            print("\n[USER]")
            print(user)
        else:
            load_dotenv()
            
            api_key = os.getenv("ANTHROPIC_API_KEY")
            model = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")
            
            gateway = ClaudeGateway(api_key, model)
            
            answer = gateway.ask(system, user)
            
            print(answer)      
    except RuntimeError as e:
        print(f"실행에러: {e}")
        exit(1)
        