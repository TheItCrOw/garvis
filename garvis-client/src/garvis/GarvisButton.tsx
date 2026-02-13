import { useEffect, useMemo, useState } from "react";
import { config } from "../config";
import { useGarvisWsClient } from "./useGarvisWsClient";
import logo from "./../assets/logo.png";
import type { GarvisInstruction } from "../models/websocket/messages";
import { analyzeXrayImgById } from "../core/xrays.api";

type GarvisButtonProps = {
  onGarvisInstruction: (instruction: GarvisInstruction) => void;
  loggedInDoctorId: number;
  analyzableXrayImg: number;
};

export default function GarvisButton({
  onGarvisInstruction,
  loggedInDoctorId,
  analyzableXrayImg,
}: GarvisButtonProps) {
  const {
    startRecording,
    stopRecording,
    isRecording,
    error,
    transcripts,
    garvisReply,
    wsIsConnected,
    garvisIsSpeaking,
    stopGarvisSpeech,
    garvisIsThinking,
  } = useGarvisWsClient({
    wsUrl: config.backendWsUrl,
    onGarvisInstruction: onGarvisInstruction,
    loggedInDoctorId: loggedInDoctorId,
    analyzableXrayImgId: analyzableXrayImg,
  });

  const [isReplyOpen, setIsReplyOpen] = useState(false);

  const hasReply = useMemo(
    () => wsIsConnected === true && !!garvisReply && garvisReply.trim() !== "",
    [wsIsConnected, garvisReply],
  );

  // optional: close if reply disappears
  // (keeps UI consistent if garvisReply is cleared elsewhere)
  if (!hasReply && isReplyOpen) {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    // (If you dislike this pattern, we can switch to useEffect.)
    setIsReplyOpen(false);
  }

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
        </div>
      ) : (
        ""
      )}
      {/* Sticky reply preview -> expands fullscreen on tap */}
      <div
        id="garvis-reply-div"
        className={isReplyOpen ? "open" : ""}
        role="button"
        tabIndex={0}
        aria-expanded={isReplyOpen}
        onClick={() => setIsReplyOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") setIsReplyOpen(true);
          if (e.key === "Escape") setIsReplyOpen(false);
        }}
      >
        <div className="garvis-reply-inner container">
          <div className="garvis-reply-header">
            <img src={logo} width={25} />
            <span className="garvis-reply-title">Garvis</span>

            <button
              type="button"
              className="garvis-reply-close"
              aria-label="Close reply"
              onClick={(e) => {
                e.stopPropagation();
                setIsReplyOpen(false);
              }}
            >
              ✕
            </button>
          </div>

          <div className="garvis-reply-body">
            {hasReply ? (
              <p className="mb-0">{garvisReply}</p>
            ) : (
              <p>Just a moment...</p>
            )}
          </div>

          {!isReplyOpen ? (
            <div className="garvis-reply-hint">Tap to expand</div>
          ) : null}
        </div>
      </div>

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
