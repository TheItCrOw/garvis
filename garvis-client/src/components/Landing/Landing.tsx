import { useState } from "react";
import "./Landing.css";
import logo from "../../assets/logo.png";

type LandingProps = {
  onEnter: (doctorId: number) => void;
};

export default function Landing({ onEnter }: LandingProps) {
  const [isExiting, setIsExiting] = useState(false);
  const [doctorId, setDoctorId] = useState<string>("");
  const [showError, setShowError] = useState<boolean>(false);

  const handleStart = () => {
    if (isExiting) return;
    if (!doctorId.trim()) {
      setShowError(true);
      return;
    }

    setIsExiting(true);
  };

  return (
    <div
      className={`landing-overlay ${isExiting ? "landing-overlay--exit" : ""}`}
      role="dialog"
      aria-modal="true"
      onTransitionEnd={(e) => {
        if (e.target === e.currentTarget && isExiting) {
          onEnter(Number.parseInt(doctorId));
        }
      }}
    >
      <div className={`landing-card ${isExiting ? "landing-card--exit" : ""}`}>
        <div className="d-flex align-items-center justify-content-center">
          <img src={logo} height={100} alt="Garvis logo" />
          <h1 className="landing-title">arvis</h1>
        </div>

        <input
          type="text"
          className="form-control w-100 text-center mt-3"
          placeholder="Your Doctor Id:"
          value={doctorId}
          onChange={(e) => setDoctorId(e.target.value)}
        />
        <p
          className="text-danger mb-0 text-center w-100 mt-1 small"
          hidden={!showError}
        >
          Please provide your Id.
        </p>

        <button
          className="landing-button mt-3"
          onClick={handleStart}
          disabled={isExiting}
        >
          Login
        </button>

        <p className="landing-hint text-dark">
          Welcome to your personal assistant.
        </p>
      </div>
    </div>
  );
}
