import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

describe("LunchPick app", () => {
  beforeEach(() => {
    window.location.hash = "#login";
    window.scrollTo = vi.fn();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith("/api/v1/meals")) return { ok: true } as Response;
      throw new Error("추천 API 데모 대체 경로");
    }));
  });

  it("starts onboarding and moves to the preference quiz", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "카카오 계정으로 로그인" }));
    expect(screen.getByRole("heading", { name: "당신의 취향을 알려주세요!" })).toBeInTheDocument();
  });

  it("renders the prototype home recommendation cards", async () => {
    window.location.hash = "#home";
    render(<App />);
    expect(await screen.findByRole("heading", { name: "오늘 뭐 먹을까요?" })).toBeInTheDocument();
    expect((await screen.findAllByText("미소된장", { exact: false })).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: "여기 갈래요 →" })).toHaveLength(3);
  });

  it("keeps skipped consent choices disabled in the profile", async () => {
    window.location.hash = "#location";
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "지금은 허용하지 않기" }));
    fireEvent.click(screen.getByRole("button", { name: "나중에 하기" }));
    fireEvent.click(screen.getByRole("button", { name: /프로필/ }));
    expect(screen.getByRole("button", { name: /알레르기·식이 유형.*미설정/ })).toBeInTheDocument();
    expect(screen.getByRole("switch", { name: "위치 정보 제공" })).not.toBeChecked();
  });

  it("opens the insight content directly from the bottom navigation", () => {
    window.location.hash = "#history";
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /인사이트/ }));
    expect(screen.getByRole("heading", { name: "한식을 가장 좋아하시네요!" })).toBeInTheDocument();
    expect(window.location.hash).toBe("#insights");
  });

  it("adds a completed meal to the current month history", async () => {
    window.location.hash = "#meal";
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /식사 기록하기/ }));
    expect(await screen.findByText("식사 기록을 저장했어요.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /좋았어요/ }));
    fireEvent.click(screen.getByRole("button", { name: "피드백 완료" }));
    fireEvent.click(screen.getByRole("button", { name: /이력/ }));
    const now = new Date();
    expect(screen.getByText(`${now.getFullYear()}년 ${now.getMonth() + 1}월`)).toBeInTheDocument();
    await waitFor(() => expect(within(screen.getByTestId(`meal-day-${now.getDate()}`)).getByTitle("미소된장")).toBeInTheDocument());
  });
});
