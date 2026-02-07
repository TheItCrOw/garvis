import { Routes, Route } from "react-router-dom";
import { useState } from "react";
import Navbar from "./components/Navbar/Navbar";
import Home from "./components/Home/Home";
import GarvisButton from "./garvis/GarvisButton";
import Landing from "./components/Landing/Landing";
import type { GarvisInstruction } from "./models/websocket/messages";

function About() {
  return <div className="container mt-4">About Garvis</div>;
}

function Settings() {
  return <div className="container mt-4">Settings</div>;
}

function App() {
  // always start locked => overlay always shows on fresh open / reload
  const [unlocked, setUnlocked] = useState(false);
  const [garvisInstruction, setGarvisInstruction] =
    useState<GarvisInstruction | null>(null);
  const [loggedInDoctorId, setLoggedInDoctorId] = useState(-1);

  const enterApp = async (doctorId: number) => {
    setLoggedInDoctorId(doctorId);
    setUnlocked(true);
  };

  return (
    <>
      <Navbar />

      {unlocked && (
        <Routes>
          <Route
            path="/"
            element={
              <Home
                garvisInstruction={garvisInstruction}
                loggedInDoctorId={loggedInDoctorId}
              />
            }
          />
          <Route path="/about" element={<About />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      )}

      {/* Only mount Garvis after the landing page is gone */}
      {unlocked && (
        <GarvisButton
          loggedInDoctorId={loggedInDoctorId}
          onGarvisInstruction={(instruction) =>
            setGarvisInstruction(instruction)
          }
        />
      )}

      {/* Fullscreen overlay on top of everything until unlocked */}
      {!unlocked && <Landing onEnter={enterApp} />}
    </>
  );
}

export default App;
