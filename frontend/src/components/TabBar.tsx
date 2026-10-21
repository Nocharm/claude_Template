import { NavLink } from "react-router-dom";

import { getLastDayId } from "../lib/storage";
import { Icon } from "./Icon";

export function TabBar() {
  const lastDayId = getLastDayId();
  const readTo = lastDayId ? `/days/${lastDayId}` : "/";
  const className = ({ isActive }: { isActive: boolean }) => (isActive ? "active" : "");

  return (
    <nav className="tabbar" aria-label="주 메뉴" data-testid="TabBar-nav">
      <NavLink to="/" end className={className} data-testid="TabBar-homeLink">
        <Icon name="home" />홈
      </NavLink>
      <NavLink
        to={readTo}
        // Without a last-read DAY this points at home; don't double-highlight the home tab.
        className={lastDayId ? className : undefined}
        data-testid="TabBar-readLink"
      >
        <Icon name="book" />
        읽기
      </NavLink>
      <NavLink to="/review" className={className} data-testid="TabBar-reviewLink">
        <Icon name="check" />
        복습
      </NavLink>
      <NavLink to="/map" className={className} data-testid="TabBar-mapLink">
        <Icon name="map" />맵
      </NavLink>
      <NavLink to="/comics" className={className} data-testid="TabBar-comicsLink">
        <Icon name="comic" />
        웹툰
      </NavLink>
    </nav>
  );
}
