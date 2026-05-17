import { Link } from "react-router-dom";

function Navbar() {
  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <div className="navbar-brand">AI Interview</div>
        <div className="navbar-links">
          <Link to="/">Home</Link>
          <Link to="/interview">Interview</Link>
          <Link to="/report">Report</Link>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
