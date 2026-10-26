import { BrowserRouter, Route, Routes } from "react-router-dom";

import { TabBar } from "./components/TabBar";
import { CharacterPage } from "./pages/CharacterPage";
import { CharactersPage } from "./pages/CharactersPage";
import { ComicPage } from "./pages/ComicPage";
import { ComicsPage } from "./pages/ComicsPage";
import { ExpressionPage } from "./pages/ExpressionPage";
import { HomePage } from "./pages/HomePage";
import { MapPage } from "./pages/MapPage";
import { ProgressPage } from "./pages/ProgressPage";
import { ReaderPage } from "./pages/ReaderPage";
import { ReviewPage } from "./pages/ReviewPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/days/:dayId" element={<ReaderPage />} />
        <Route path="/expressions/:expressionId" element={<ExpressionPage />} />
        <Route path="/map" element={<MapPage />} />
        <Route path="/review" element={<ReviewPage />} />
        <Route path="/progress" element={<ProgressPage />} />
        <Route path="/comics" element={<ComicsPage />} />
        <Route path="/comics/:comicId" element={<ComicPage />} />
        <Route path="/characters" element={<CharactersPage />} />
        <Route path="/characters/:characterId" element={<CharacterPage />} />
      </Routes>
      <TabBar />
    </BrowserRouter>
  );
}
