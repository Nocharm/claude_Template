import { fireEvent, render, screen } from "@testing-library/react";

import type { QuizItem } from "../api";
import { QuizCard } from "./QuizCard";

const item: QuizItem = {
  expression_id: 7,
  day_no: 3,
  kind: "cloze",
  prompt_ko: "나오기 전에 일기 예보 확인했어?",
  prompt_en: '"Did you check the weather forecast before we ____?" I asked.',
  hint: "c",
  is_new: true,
};

function renderCard(isCorrect: boolean) {
  const onCheck = vi.fn().mockResolvedValue({
    is_correct: isCorrect,
    expected: "came out",
    meaning_ko: "나오다",
  });
  const onGrade = vi.fn();
  render(<QuizCard item={item} onCheck={onCheck} onGrade={onGrade} />);
  return { onCheck, onGrade };
}

describe("QuizCard", () => {
  it("checks the answer, fills the blank and grades good", async () => {
    // Arrange
    const { onCheck, onGrade } = renderCard(true);

    // Act
    fireEvent.change(screen.getByTestId("QuizCard-answerInput"), {
      target: { value: "came out" },
    });
    fireEvent.click(screen.getByTestId("QuizCard-checkButton"));
    fireEvent.click(await screen.findByTestId("QuizCard-goodButton"));

    // Assert
    expect(onCheck).toHaveBeenCalledWith("came out");
    expect(screen.getByTestId("QuizCard-feedback")).toHaveTextContent("정답이에요!");
    expect(onGrade).toHaveBeenCalledWith("good");
  });

  it("offers only 'again' after a wrong answer", async () => {
    const { onGrade } = renderCard(false);

    fireEvent.change(screen.getByTestId("QuizCard-answerInput"), { target: { value: "go out" } });
    fireEvent.click(screen.getByTestId("QuizCard-checkButton"));
    fireEvent.click(await screen.findByTestId("QuizCard-againButton"));

    expect(screen.queryByTestId("QuizCard-goodButton")).not.toBeInTheDocument();
    expect(onGrade).toHaveBeenCalledWith("again");
  });
});
