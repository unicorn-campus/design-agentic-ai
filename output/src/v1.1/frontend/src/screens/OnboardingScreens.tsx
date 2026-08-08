import { useState } from "react";
import { allergens, dietTypes, foods, type Route } from "../data";
import { Header, Page } from "../components/Chrome";

type Navigate = (route: Route) => void;

export function LoginScreen({ navigate }: { navigate: Navigate }) {
  return (
    <main className="login-screen">
      <div className="login-brandmark" aria-hidden="true">🍽️</div>
      <h1 className="login-brand">런치픽</h1>
      <p className="login-subtitle">3분이면 당신만의<br />점심 파트너가 완성돼요</p>
      <button className="login-kakao" onClick={() => navigate("quiz")} aria-label="카카오 계정으로 로그인">
        <span aria-hidden="true">💬</span> 카카오로 시작하기
      </button>
      <p className="login-legal">로그인 시 이용약관 및 개인정보처리방침에<br />동의하는 것으로 간주합니다.</p>
    </main>
  );
}

export function QuizScreen({ navigate }: { navigate: Navigate }) {
  const [index, setIndex] = useState(0);
  const [direction, setDirection] = useState<"like" | "dislike" | null>(null);
  const complete = index >= foods.length;
  const swipe = (next: "like" | "dislike") => {
    setDirection(next);
    window.setTimeout(() => {
      setIndex((value) => value + 1);
      setDirection(null);
    }, 180);
  };

  return (
    <>
      <Header title="취향 퀴즈" back="login" navigate={navigate} />
      <Page>
        <div className="quiz-header">
          <span className="caption">{Math.min(index + 1, foods.length)} / {foods.length}</span>
          <button className="btn-text" onClick={() => navigate("location")}>건너뛰기</button>
        </div>
        <div className="progress-bar" aria-label="퀴즈 진행률">
          <div className="progress-bar__fill" style={{ width: `${(Math.min(index, foods.length) / foods.length) * 100}%` }} />
        </div>
        {!complete ? (
          <section className="quiz-content">
            <h1>당신의 취향을 알려주세요!</h1>
            <p>좋아하는 음식은 오른쪽, 별로라면 왼쪽</p>
            <article className={`quiz-food-card ${direction ? `quiz-food-card--${direction}` : ""}`}>
              <div className="quiz-food-card__emoji">{foods[index].emoji}</div>
              <h2>{foods[index].name}</h2>
              <p>{foods[index].tags}</p>
            </article>
            <div className="quiz-actions">
              <button className="quiz-round quiz-round--dislike" onClick={() => swipe("dislike")} aria-label="싫어요">👎</button>
              <span className="caption">선택할수록 추천이 정교해져요</span>
              <button className="quiz-round quiz-round--like" onClick={() => swipe("like")} aria-label="좋아요">👍</button>
            </div>
          </section>
        ) : (
          <section className="completion-panel">
            <div className="completion-emoji">✨</div>
            <h1>취향 프로파일 완성!</h1>
            <p>이제 준혁님에게 맞는 점심을 찾을 수 있어요.</p>
            <button className="btn btn-primary btn-full" onClick={() => navigate("location")}>다음으로</button>
          </section>
        )}
      </Page>
    </>
  );
}

export function LocationScreen({ navigate }: { navigate: Navigate }) {
  return (
    <>
      <Header back="quiz" navigate={navigate} />
      <Page>
        <section className="consent-screen">
          <div className="consent-visual" aria-hidden="true"><span>📍</span></div>
          <h1>위치 정보를 허용해주세요</h1>
          <p>현재 위치를 기준으로 걸어서 갈 수 있는<br />맛집을 찾아드려요.</p>
          <div className="privacy-card">
            <span>🛡️</span>
            <div><strong>위치는 추천에만 사용해요</strong><p>동의는 프로필에서 언제든 변경할 수 있어요.</p></div>
          </div>
          <div className="stack-actions">
            <button className="btn btn-primary btn-full" onClick={() => navigate("dietary")}>위치 정보 허용하기</button>
            <button className="btn btn-secondary btn-full" onClick={() => navigate("dietary")}>지금은 허용하지 않기</button>
          </div>
        </section>
      </Page>
    </>
  );
}

export function DietaryScreen({ navigate }: { navigate: Navigate }) {
  const [consent, setConsent] = useState(false);
  const [selectedAllergens, setSelectedAllergens] = useState<string[]>([]);
  const [diet, setDiet] = useState("일반");
  const toggle = (value: string) => setSelectedAllergens((current) => current.includes(value)
    ? current.filter((item) => item !== value)
    : [...current, value]);

  return (
    <>
      <Header title="식이제한 설정" back="location" navigate={navigate} />
      <Page>
        <div className="skip-row"><span>안전한 추천을 위해 알려주세요</span><button className="btn-text" onClick={() => navigate("home")}>나중에 하기</button></div>
        <label className="consent-check">
          <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} />
          <span><strong>건강 관련 정보 수집에 동의합니다</strong><small>알레르기·식이 정보는 안전 추천에만 사용됩니다.</small></span>
        </label>
        <section className="diet-section">
          <h2>알레르기 항목</h2><p>해당하는 알레르기를 모두 선택해주세요.</p>
          <div className="chip-group">
            {allergens.map((item) => <button key={item} className={`chip ${selectedAllergens.includes(item) ? "selected" : ""}`} onClick={() => toggle(item)}>{item}</button>)}
          </div>
        </section>
        <section className="diet-section">
          <h2>식이 유형</h2><p>현재 지키는 식이 유형을 선택해주세요.</p>
          <div className="chip-group">
            {dietTypes.map((item) => <button key={item} className={`chip ${diet === item ? "selected" : ""}`} onClick={() => setDiet(item)}>{item}</button>)}
          </div>
        </section>
        <button className="btn btn-primary btn-full dietary-submit" disabled={!consent} onClick={() => navigate("home")}>설정 완료</button>
      </Page>
    </>
  );
}
