import { splitHighlights } from "./highlight";

describe("splitHighlights", () => {
  it("marks highlights case- and quote-insensitively, in text order", () => {
    // Arrange
    const text = "But after a while, Something didn’t feel quite right. We spotted it.";
    const marks = [
      { id: 2, highlight: "spotted" },
      { id: 1, highlight: "something didn't feel quite right" },
    ];

    // Act
    const segments = splitHighlights(text, marks);

    // Assert
    expect(segments).toEqual([
      { text: "But after a while, ", markId: null },
      { text: "Something didn’t feel quite right", markId: 1 },
      { text: ". We ", markId: null },
      { text: "spotted", markId: 2 },
      { text: " it.", markId: null },
    ]);
  });

  it("skips empty, missing and overlapping highlights", () => {
    const text = "have always been thrill-seekers";
    const marks = [
      { id: 1, highlight: "have always been" },
      { id: 2, highlight: "always" },
      { id: 3, highlight: "" },
      { id: 4, highlight: "not here" },
    ];

    const segments = splitHighlights(text, marks);

    expect(segments).toEqual([
      { text: "have always been", markId: 1 },
      { text: " thrill-seekers", markId: null },
    ]);
  });
});
