import logo from "../../assets/logo.png";
import TalkButton from "../../audio/TalkButton";
import "./Home.css";

export default function Home() {
  return (
    <div className="container py-4">
      <h1 className="mb-3">Garvis</h1>
      <img src={logo} alt="Garvis logo" width={140} />
      <TalkButton />
    </div>
  );
}
