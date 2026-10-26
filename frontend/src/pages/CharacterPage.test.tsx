import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { api, type CharacterDetail } from "../api";
import { CharacterPage } from "./CharacterPage";

const draft: CharacterDetail = {
  id: 3,
  name: "Sora",
  appearance: "coworker, long red hair",
  status: "draft",
  final_version: null,
  image_url: "/api/characters/3/versions/2/image",
  version_count: 2,
  versions: [
    { no: 1, instruction: "coworker, long red hair", image_url: "/v1" },
    { no: 2, instruction: "add round glasses", image_url: "/v2" },
  ],
};

function renderPage() {
  render(
    <MemoryRouter initialEntries={["/characters/3"]}>
      <Routes>
        <Route path="/characters/:characterId" element={<CharacterPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("CharacterPage", () => {
  it("revises from the selected version and finalizes the chosen one", async () => {
    // Arrange
    vi.spyOn(api, "getCharacter").mockResolvedValue(draft);
    const revise = vi.spyOn(api, "reviseCharacter").mockResolvedValue({
      ...draft,
      versions: [...draft.versions, { no: 3, instruction: "short hair", image_url: "/v3" }],
    });
    const finalize = vi
      .spyOn(api, "finalizeCharacter")
      .mockResolvedValue({ ...draft, status: "active", final_version: 1 });
    renderPage();

    // Act: pick v1, ask for a change, then go back to v1 and finalize it
    fireEvent.click(await screen.findByTestId("CharacterPage-version-1"));
    fireEvent.change(screen.getByTestId("CharacterPage-instructionInput"), {
      target: { value: "short hair" },
    });
    fireEvent.click(screen.getByTestId("CharacterPage-reviseButton"));
    fireEvent.click(await screen.findByTestId("CharacterPage-version-3"));
    fireEvent.click(screen.getByTestId("CharacterPage-version-1"));
    fireEvent.click(screen.getByTestId("CharacterPage-finalizeButton"));

    // Assert
    expect(revise).toHaveBeenCalledWith(3, 1, "short hair");
    expect(finalize).toHaveBeenCalledWith(3, 1);
    expect(await screen.findByTestId("CharacterPage-statusButton")).toHaveTextContent("잠시 빼기");
  });
});
