import { NavLink } from "react-router-dom";
import "./Navbar.css";
import logo from "../../assets/logo.png";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faUser } from "@fortawesome/free-solid-svg-icons";

export default function Navbar() {
  return (
    <nav className="navbar navbar-expand-lg bg-light">
      <div className="container">
        <NavLink className="navbar-brand fw-bold" to="/">
          <div className="d-flex align-items-center">
            <img src={logo} height={40} />
            <h2
              className="mb-0 text-primary fw-bold"
              style={{ fontSize: "25px" }}
            >
              arvis
            </h2>
          </div>
        </NavLink>

        <button
          className="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#navbarNav"
        >
          <span className="navbar-toggler-icon" />
        </button>

        <div className="collapse navbar-collapse" id="navbarNav">
          <div className="navbar-nav ms-auto mt-3 mb-3">
            <div className="nav-item w-100 text-center">
              <NavLink className="nav-link" to="/login">
                <h5 className="mb-0">User</h5>
                <FontAwesomeIcon icon={faUser} className="ms-1" />
              </NavLink>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
