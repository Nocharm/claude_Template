import { fireEvent, render, screen } from "@testing-library/react";

import { playTts } from "../lib/speech";
import { getVoicePrefs } from "../lib/storage";
import { SpeakControls } from "./SpeakControls";

vi.mock("../lib/speech", () => ({ playTts: vi.fn().mockResolvedValue(undefined) }));

describe("SpeakControls", () => {
  beforeEach(() => localStorage.clear());

  it("plays in the tapped accent and remembers it with the slow setting", () => {
    // Arrange
    render(<SpeakControls text="have always been ~" />);

    // Act
    fireEvent.click(screen.getByTestId("SpeakControls-accent-uk"));
    fireEvent.click(screen.getByTestId("SpeakControls-slowToggle"));

    // Assert
    expect(playTts).toHaveBeenNthCalledWith(1, "have always been ~", "uk", false);
    expect(playTts).toHaveBeenNthCalledWith(2, "have always been ~", "uk", true);
    expect(screen.getByTestId("SpeakControls-accent-uk")).toHaveAttribute("aria-pressed", "true");
    expect(getVoicePrefs()).toEqual({ accent: "uk", isSlow: true });
  });
});
