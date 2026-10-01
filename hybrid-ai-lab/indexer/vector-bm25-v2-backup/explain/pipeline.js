(() => {
  'use strict';

  const tabs = [...document.querySelectorAll('[role="tab"][data-step]')];
  const panels = [...document.querySelectorAll('[role="tabpanel"][data-panel]')];
  const previousButton = document.querySelector('[data-prev]');
  const nextButton = document.querySelector('[data-next]');
  const panelCount = document.querySelector('.panel-count b');
  let activeStep = 0;

  function showStep(index, { focus = false } = {}) {
    const safeIndex = Math.max(0, Math.min(index, tabs.length - 1));
    activeStep = safeIndex;
    tabs.forEach((tab, tabIndex) => {
      const selected = tabIndex === safeIndex;
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
    panels.forEach((panel, panelIndex) => {
      const selected = panelIndex === safeIndex;
      panel.hidden = !selected;
      panel.classList.toggle('is-active', selected);
    });
    previousButton.disabled = safeIndex === 0;
    nextButton.innerHTML = safeIndex === tabs.length - 1
      ? '첫 단계로 <span aria-hidden="true">↺</span>'
      : '다음 단계 <span aria-hidden="true">→</span>';
    panelCount.textContent = String(safeIndex + 1);
    if (focus) tabs[safeIndex].focus();
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => showStep(index));
    tab.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      if (event.key === 'Home') return showStep(0, { focus: true });
      if (event.key === 'End') return showStep(tabs.length - 1, { focus: true });
      const delta = event.key === 'ArrowRight' ? 1 : -1;
      showStep((index + delta + tabs.length) % tabs.length, { focus: true });
    });
  });
  previousButton.addEventListener('click', () => showStep(activeStep - 1));
  nextButton.addEventListener('click', () => showStep(activeStep === tabs.length - 1 ? 0 : activeStep + 1));

  const cleanCard = document.querySelector('[data-clean-card]');
  const cleanButtons = [...document.querySelectorAll('[data-clean-view]')];
  const validationRow = document.querySelector('.validation-row');
  cleanButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const after = button.dataset.cleanView === 'after';
      cleanButtons.forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
      cleanCard.classList.toggle('is-after', after);
      cleanCard.querySelectorAll('[data-redactable]').forEach((item) => {
        item.textContent = after ? '[삭제]' : item.dataset.original;
      });
      validationRow.classList.toggle('is-ready', after);
      validationRow.setAttribute('aria-label', after ? '정제 후 수행하는 검증 항목' : '정제 후 수행할 검증 항목');
    });
  });

  const boundaryDetails = {
    D1: '<b>D1 · 조항 경계</b><span><code>제 N조(제목)</code>이 시작되는 곳을 먼저 나눕니다.</span><small>예: 제 N조(제목) → 다음 조항 전까지 같은 규칙 맥락 유지</small>',
    D2: '<b>D2 · 카드·혜택 ID 경계</b><span><code>D2-C001</code>이나 <code>D2-C001-B01</code>이 시작되는 곳을 먼저 나눕니다.</span><small>예: 카드 단위와 세부 혜택 단위를 식별하는 ID 경계</small>',
    D3: '<b>D3 · 발화자 경계</b><span><code>고객:</code> 또는 <code>상담사:</code>가 시작되는 곳을 먼저 나눕니다.</span><small>예: 고객: 같은 요청이 반복돼요. / 상담사: 멈춘 단계를 확인하겠습니다.</small>'
  };
  const boundaryOutput = document.querySelector('[data-boundary-output]');
  document.querySelectorAll('[data-boundary]').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('[data-boundary]').forEach((item) => item.classList.remove('is-selected'));
      button.classList.add('is-selected');
      boundaryOutput.innerHTML = boundaryDetails[button.dataset.boundary];
    });
  });

  const vectorOutput = document.querySelector('.vector-output');
  document.querySelectorAll('[data-vector]').forEach((point) => {
    point.addEventListener('click', () => {
      vectorOutput.textContent = point.dataset.vector;
    });
  });

  const glossary = document.querySelector('[data-glossary]');
  document.querySelector('[data-open-glossary]').addEventListener('click', () => {
    if (typeof glossary.showModal === 'function') glossary.showModal();
    else glossary.setAttribute('open', '');
  });
  document.querySelector('[data-close-glossary]').addEventListener('click', () => glossary.close());
  glossary.addEventListener('click', (event) => {
    if (event.target === glossary) glossary.close();
  });

  const answers = [
    { correct: 'b', ok: '맞습니다. 로더는 원문과 함께 제거·치환 좌표를 메모리에 기록합니다.', no: '로드 단계에서는 원문 좌표를 기록합니다. 실제 치환은 청킹 뒤 정제 단계에서 이뤄집니다.' },
    { correct: 'b', ok: '맞습니다. 200토큰은 최대치이며 문서 경계에 따라 실제 중첩은 더 작을 수 있습니다.', no: '설정의 200은 고정값이 아니라 중첩 상한입니다.' },
    { correct: 'a', ok: '맞습니다. 벡터는 의미 유사도를, BM25는 정확한 단어 일치를 보완합니다.', no: '두 색인은 서로 다른 검색 강점을 같은 청크에 연결하기 위해 만듭니다.' }
  ];
  const questionStates = new Array(answers.length).fill(false);
  const quiz = document.querySelector('[data-quiz]');

  quiz.addEventListener('change', (event) => {
    if (!(event.target instanceof HTMLInputElement)) return;
    const fieldset = event.target.closest('[data-question]');
    const index = Number(fieldset.dataset.question);
    const correct = event.target.value === answers[index].correct;
    questionStates[index] = correct;
    fieldset.classList.toggle('is-correct', correct);
    fieldset.classList.toggle('is-wrong', !correct);
    fieldset.querySelector('output').textContent = correct ? answers[index].ok : answers[index].no;
    const score = questionStates.filter(Boolean).length;
    const completed = [...quiz.querySelectorAll('fieldset')].every((item) => item.querySelector('input:checked'));
    quiz.querySelector('.quiz-result span').textContent = completed
      ? (score === answers.length ? '좋습니다. 핵심 원리를 모두 이해했습니다.' : '틀린 답의 설명을 읽고 다시 선택해 보세요.')
      : '선택한 문제부터 바로 채점하고 있습니다.';
    quiz.querySelector('.quiz-result strong').textContent = `${score} / ${answers.length}`;
  });

  const counters = [...document.querySelectorAll('[data-count]')];
  let counted = false;
  const runCounters = () => {
    if (counted) return;
    counted = true;
    counters.forEach((counter) => {
      const target = Number(counter.dataset.count);
      if (target === 0 || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        counter.textContent = String(target);
        return;
      }
      const start = performance.now();
      const duration = 750;
      const tick = (now) => {
        const progress = Math.min(1, (now - start) / duration);
        counter.textContent = String(Math.round(target * (1 - Math.pow(1 - progress, 3))));
        if (progress < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
  };

  const evidence = document.querySelector('#evidence');
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        runCounters();
        observer.disconnect();
      }
    }, { threshold: 0.25 });
    observer.observe(evidence);
  } else {
    runCounters();
  }

  showStep(0);
})();
