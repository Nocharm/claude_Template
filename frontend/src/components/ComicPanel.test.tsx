import { fireEvent, render, screen } from "@testing-library/react";

import type { ComicBubble } from "../api";
import { ComicPanel } from "./ComicPanel";

const bubbles: ComicBubble[] = [
  {
    speaker: "mina",
    text_en: "Look, I spotted scooters!",
    text_ko: "봐, 스쿠터 발견!",
    highlight: "spotted",
  },
  { speaker: "jun", text_en: "I'm down!", text_ko: "좋아!", highlight: "I'm down" },
];

describe("ComicPanel", () => {
  it("overlays bubbles with markers, optional Korean, and speaks on tap", () => {
    // Arrange
    const onSpeak = vi.fn();
    const { rerender } = render(
      <ComicPanel
        no={2}
        imageUrl="/api/comics/1/panels/2"
        bubbles={bubbles}
        isKoreanShown={false}
        onSpeak={onSpeak}
      />,
    );

    // Act
    fireEvent.click(screen.getByTestId("ComicPanel-bubble-2-1"));
    rerender(
      <ComicPanel
        no={2}
        imageUrl="/api/comics/1/panels/2"
        bubbles={bubbles}
        isKoreanShown
        onSpeak={onSpeak}
      />,
    );

    // Assert
    expect(onSpeak).toHaveBeenCalledWith("I'm down!");
    expect(screen.getByText("spotted")).toHaveClass("marker");
    expect(screen.getByText("좋아!")).toBeInTheDocument();
    expect(screen.getByRole("img")).toHaveAttribute("src", "/api/comics/1/panels/2");
  });
});
