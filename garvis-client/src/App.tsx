import { useState } from "react";
import logo from "./assets/logo.png";
import "./App.css";

function App() {
  //const [count, setCount] = useState(0);

  return (
    <>
      <div className="container">
        <h1>Garvis</h1>
        <img src={logo} />
      </div>
    </>
  );
}

export default App;
