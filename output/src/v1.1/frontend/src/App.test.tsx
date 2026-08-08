import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

describe("LunchPick app", () => {
  beforeEach(() => {
    window.location.hash = "#login";
    window.scrollTo = vi.fn();
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
});
