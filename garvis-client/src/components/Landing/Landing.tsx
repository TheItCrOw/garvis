import { useState } from "react";
import "./Landing.css";
import logo from "../../assets/logo.png";

type LandingProps = {
  onEnter: () => void;
};

export default function Landing({ onEnter }: LandingProps) {
  const [isExiting, setIsExiting] = useState(false);

  const handleStart = () => {
    if (isExiting) return;
    setIsExiting(true);
  };

  return (
    <div
      className={`landing-overlay ${isExiting ? "landing-overlay--exit" : ""}`}
      role="dialog"
      aria-modal="true"
      onTransitionEnd={(e) => {
        if (e.target === e.currentTarget && isExiting) {
          onEnter();
        }
      }}
    >
      <div className={`landing-card ${isExiting ? "landing-card--exit" : ""}`}>
        <div className="d-flex align-items-center justify-content-center">
          <img src={logo} height={100} alt="Garvis logo" />
          <h1 className="landing-title">arvis</h1>
        </div>

        <button
          className="landing-button"
          onClick={handleStart}
          disabled={isExiting}
        >
          Start
        </button>

        <p className="landing-hint text-dark">
          Welcome to your personal assistant.
        </p>
      </div>
    </div>
  );
}
