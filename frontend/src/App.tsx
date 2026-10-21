import { BrowserRouter, Route, Routes } from "react-router-dom";

import { TabBar } from "./components/TabBar";
import { ExpressionPage } from "./pages/ExpressionPage";
import { HomePage } from "./pages/HomePage";
import { MapPage } from "./pages/MapPage";
import { ReaderPage } from "./pages/ReaderPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/days/:dayId" element={<ReaderPage />} />
        <Route path="/expressions/:expressionId" element={<ExpressionPage />} />
        <Route path="/map" element={<MapPage />} />
      </Routes>
      <TabBar />
    </BrowserRouter>
  );
}
