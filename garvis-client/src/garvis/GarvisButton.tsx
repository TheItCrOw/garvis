import { config } from "../config";
import { useGarvisWsClient } from "./useGarvisWsClient";
import logo from "./../assets/logo.png";
import type { GarvisInstruction } from "../models/websocket/messages";

type GarvisButtonProps = {
  onGarvisInstruction: (instruction: GarvisInstruction) => void;
  loggedInDoctorId: number;
};

export default function GarvisButton({
  onGarvisInstruction,
  loggedInDoctorId,
}: GarvisButtonProps) {
  const {
    startRecording,
    stopRecording,
    isRecording,
    error,
    transcripts,
    wsIsConnected,
    garvisIsSpeaking,
    stopGarvisSpeech,
    garvisIsThinking,
  } = useGarvisWsClient({
    wsUrl: config.backendWsUrl,
    onGarvisInstruction: onGarvisInstruction,
    loggedInDoctorId: loggedInDoctorId,
  });

  return (
    <div>
      {wsIsConnected == true ? (
        <div id="talk-garvis-container">
          {isRecording ? (
            <label id="talk-garvis-recoding-label">Yes?</label>
          ) : (
            ""
          )}
          <button
            id="talk-garvis-btn"
            className={[
              isRecording ? "is-recording" : "",
              garvisIsSpeaking ? "is-speaking" : "",
              garvisIsThinking ? "is-thinking" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            onPointerDown={() => startRecording()}
            onPointerUp={() => stopRecording()}
            onPointerCancel={() => stopRecording()}
            onPointerLeave={() => stopRecording()}
          >
            <img src={logo} alt="Garvis logo" width={50} />
          </button>
          {error && <div id="talk-garvis-error-msg">{error}</div>}
          {/* {garvisIsSpeaking && (
            <button
              id="stop-garvis-speech-btn"
              className="btn"
              onClick={stopGarvisSpeech}
            >
              <FontAwesomeIcon icon={faStop} />
            </button>
          )} */}
        </div>
      ) : (
        ""
      )}

      {/* The dropdown which shows what's being transcribed and understood by Garvis */}
      {wsIsConnected == true ? (
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
      ) : (
        ""
      )}
    </div>
  );
}
