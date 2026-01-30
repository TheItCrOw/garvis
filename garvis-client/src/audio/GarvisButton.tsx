import { config } from "../config";
import { useGarvisWsClient } from "./useGarvisWsClient";
import logo from "./../assets/logo.png";

export default function GarvisButton() {
  const { start, stop, isRecording, error, transcripts } = useGarvisWsClient({
    wsUrl: config.backendWsUrl,
  });

  return (
    <div>
      <div id="talk-garvis-container">
        {isRecording ? <label id="talk-garvis-recoding-label">Yes?</label> : ""}
        <button
          id="talk-garvis-btn"
          className={`btn ${isRecording ? "is-recording" : ""}`}
          onPointerDown={() => start()}
          onPointerUp={() => stop()}
          onPointerCancel={() => stop()}
          onPointerLeave={() => stop()}
        >
          <img src={logo} alt="Garvis logo" width={50} />
        </button>
        {error && <div id="talk-garvis-error-msg">{error}</div>}
      </div>

      {/* The dropdown which shows what's being transcribed and understood by Garvis */}
      <div
        id="garvis-transcription-div"
        className={isRecording == false ? "" : "open"}
      >
        <div className="backdrop"></div>
        <div className="history">
          {transcripts.length === 0 && (
            <span className="history-empty" style={{ fontSize: "3rem" }}>
              Yes?
            </span>
          )}

          {transcripts.map((text, idx) => (
            <span key={idx} className="history-item text-center">
              {text}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
