import { Routes, Route } from "react-router-dom";
import { useState } from "react";
import Navbar from "./components/Navbar/Navbar";
import Home from "./components/Home/Home";
import GarvisButton from "./audio/GarvisButton";
import Landing from "./components/Landing/Landing";

function About() {
  return <div className="container mt-4">About Garvis</div>;
}

function Settings() {
  return <div className="container mt-4">Settings</div>;
}

function App() {
  // always start locked => overlay always shows on fresh open / reload
  const [unlocked, setUnlocked] = useState(false);

  const enterApp = async () => {
    setUnlocked(true);
  };

  return (
    <>
      <Navbar />

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/about" element={<About />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>

      {/* Only mount Garvis after the landing page is gone */}
      {unlocked && <GarvisButton />}

      {/* Fullscreen overlay on top of everything until unlocked */}
      {!unlocked && <Landing onEnter={enterApp} />}
    </>
  );
}

export default App;
