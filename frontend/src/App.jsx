import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

import Home from "./pages/Home";
import Interview from "./pages/Interview";
import Report from "./pages/Report";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/interview" element={<Interview />} />
        <Route path="/report" element={<Report />} />
      </Routes>
    </Router>
  );
}

export default App;