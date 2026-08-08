import type { ReactNode } from "react";
import type { Route } from "../data";

interface HeaderProps {
  title?: string;
  location?: boolean;
  back?: Route;
  navigate: (route: Route) => void;
}

export function Header({ title, location, back, navigate }: HeaderProps) {
  return (
    <header className="app-header" role="banner">
      <div className="app-header__inner">
        {back && (
          <button className="btn-icon app-header__back" aria-label="뒤로 가기" onClick={() => navigate(back)}>
            ←
          </button>
        )}
        {location && <div className="app-header__location">📍 강남역 근처</div>}
        {title && <div className="app-header__title">{title}</div>}
        <div className="app-header__spacer" />
        {location && <button className="btn-icon" aria-label="알림">🔔</button>}
      </div>
    </header>
  );
}

const tabs: Array<{ id: Route; label: string; icon: string }> = [
  { id: "home", label: "홈", icon: "🏠" },
  { id: "history", label: "이력", icon: "📋" },
  { id: "insights", label: "인사이트", icon: "📊" },
  { id: "profile", label: "프로필", icon: "👤" },
];

export function BottomNav({ active, navigate }: { active: Route; navigate: (route: Route) => void }) {
  return (
    <nav className="bottom-nav" aria-label="주 메뉴">
      {tabs.map((tab, index) => (
        <button
          key={`${tab.label}-${index}`}
          className={`bottom-nav__tab ${active === tab.id ? "bottom-nav__tab--active" : ""}`}
          aria-current={active === tab.id ? "page" : undefined}
          onClick={() => navigate(tab.id)}
        >
          <span className="bottom-nav__icon">{tab.icon}</span>
          <span className="bottom-nav__label">{tab.label}</span>
        </button>
      ))}
    </nav>
  );
}

export function Modal({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label={title} onMouseDown={onClose}>
      <div className="modal" onMouseDown={(event) => event.stopPropagation()}>
        <div className="modal-heading">
          <h3 className="modal__title">{title}</h3>
          <button className="btn-icon" aria-label="닫기" onClick={onClose}>×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Page({ children }: { children: ReactNode }) {
  return <main className="page-container">{children}</main>;
}
