import { useState, useRef } from "react";
import { transcribeMedicalAudio } from "./../../core/medasr.api";
import "./NoteRecordButton.css";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faMicrophone,
  faStop,
  faUserDoctor,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";
import listeningSound from "./../../assets/audio/listening.mp3";
import understoodSound from "./../../assets/audio/understood.mp3";

export default function NoteRecordButton() {
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const [transcription, setTranscription] = useState<string>("");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  function playSound(sound: string): Promise<void> {
    return new Promise((resolve) => {
      const audio = new Audio(sound);
      audio.volume = 0.6;

      audio.onended = () => resolve();

      // Fallback resolve in case onended doesn’t fire
      setTimeout(resolve, 1200);

      audio.play().catch(() => resolve());
    });
  }

  async function startRecording() {
    // If result is open, close it when starting a new recording
    setShowResult(false);
    setTranscription("");

    playSound(listeningSound);

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    const mediaRecorder = new MediaRecorder(stream);
    mediaRecorderRef.current = mediaRecorder;
    audioChunksRef.current = [];

    mediaRecorder.ondataavailable = (event) => {
      audioChunksRef.current.push(event.data);
    };

    mediaRecorder.onstop = async () => {
      // Important: many browsers record as webm/ogg; don't force wav here.
      const audioBlob = new Blob(audioChunksRef.current);
      setIsLoading(true);
      playSound(understoodSound);

      try {
        const result = await transcribeMedicalAudio(audioBlob);

        let text = result?.text ?? "";
        if (text.length < 2) text = "Nothing recorded.";
        setTranscription(text);
        setShowResult(true);
      } catch (err) {
        console.error(err);
        setTranscription("Transcription failed.");
        setShowResult(true);
      } finally {
        // stop mic tracks so the browser releases the mic
        stream.getTracks().forEach((t) => t.stop());
        setIsLoading(false);
      }
    };

    mediaRecorder.start();
    setIsRecording(true);
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  }

  function handleClick() {
    if (!isRecording) startRecording();
    else stopRecording();
  }

  return (
    <>
      <button
        className={`note-record-btn ${isRecording ? "recording" : ""}`}
        onClick={handleClick}
      >
        {isRecording ? (
          <FontAwesomeIcon icon={faStop} size="xl" />
        ) : (
          <div className="d-flex">
            <FontAwesomeIcon icon={faUserDoctor} size="xl" />
            <FontAwesomeIcon icon={faMicrophone} size="xl" />
          </div>
        )}
      </button>

      {(isRecording || isLoading) && (
        <div className="recording-div">
          <div className="backdrop"></div>
          <p className="listening-message">
            {isLoading
              ? "Transcribing, one second..."
              : "Listening. Ready to take your notes."}
          </p>
        </div>
      )}

      {showResult && !isRecording && (
        <div className="recording-result">
          <div className="result-backdrop"></div>

          <div className="result-card">
            <button
              className="result-close"
              onClick={() => setShowResult(false)}
              aria-label="Close transcription"
            >
              <FontAwesomeIcon icon={faXmark} />
            </button>

            <h3 className="result-title">MedASR Transcription</h3>
            <p className="result-text text-secondary">{transcription}</p>
            <div className="d-flex align-items-center mt-3 justify-content-center w-100">
              <button className="btn btn-light text-success w-100">Save</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
