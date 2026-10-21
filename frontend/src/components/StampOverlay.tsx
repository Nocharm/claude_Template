interface StampOverlayProps {
  xpBonus: number;
  onClose: () => void;
}

/** Full-screen "goal met" celebration with the stamp animation. */
export function StampOverlay({ xpBonus, onClose }: StampOverlayProps) {
  return (
    <div
      className="stamp-overlay"
      role="dialog"
      aria-label="오늘 목표 달성"
      data-testid="StampOverlay-dialog"
    >
      <div className="stamp">
        <span style={{ fontSize: 34 }}>참 잘했어요</span>
        <span style={{ fontSize: 18, paddingTop: 6 }}>오늘 목표 달성</span>
      </div>
      <span className="number" style={{ color: "var(--green)", fontSize: 20 }}>
        +{xpBonus} XP
      </span>
      <button
        type="button"
        className="button"
        onClick={onClose}
        data-testid="StampOverlay-closeButton"
      >
        계속하기
      </button>
    </div>
  );
}
