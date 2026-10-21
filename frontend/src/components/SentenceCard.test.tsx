import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import type { Sentence } from "../api";
import { SentenceCard } from "./SentenceCard";

const sentence: Sentence = {
  id: 10,
  no: 5,
  text_en: "But after a while, something didn't feel quite right.",
  text_ko: "하지만 조금 지나고 나자 뭔가 이상한 느낌이 들었다.",
  expressions: [
    {
      id: 42,
      text: "Something didn't feel quite right.",
      highlight: "something didn't feel quite right",
      meaning_ko: "뭔가 이상한 느낌이 들었다.",
    },
  ],
};

describe("SentenceCard", () => {
  it("flips to the translation on tap and links each expression", () => {
    // Arrange
    render(
      <MemoryRouter>
        <SentenceCard sentence={sentence} />
      </MemoryRouter>,
    );
    const card = screen.getByTestId("SentenceCard-flip-5");

    // Act
    fireEvent.click(card);

    // Assert
    expect(card).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText(sentence.text_ko)).toBeInTheDocument();
    expect(screen.getByText("something didn't feel quite right")).toHaveClass("marker");
    expect(screen.getByTestId("SentenceCard-expression-42")).toHaveAttribute(
      "href",
      "/expressions/42",
    );
  });
});
