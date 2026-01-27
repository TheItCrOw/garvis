import { config } from "../config";
import { usePushToTalkAudio } from "./usePushToTalkAudio";

export default function TalkButton() {
  const { start, stop, isRecording, error } = usePushToTalkAudio({
    wsUrl: config.backendWsUrl,
  });

  return (
    <div className="container py-4">
      <button
        className={`btn ${isRecording ? "btn-danger" : "btn-primary"}`}
        onPointerDown={() => start()}
        onPointerUp={() => stop()}
        onPointerCancel={() => stop()}
        onPointerLeave={() => stop()}
      >
        {isRecording ? "Listening…" : "Hold to talk"}
      </button>

      {error && <div className="text-danger mt-2">{error}</div>}
    </div>
  );
}
