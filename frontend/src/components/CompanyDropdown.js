import React from "react";

function CompanyDropdown({ setCompany }) {
  return (
    <div>
      <h3>Select Company</h3>

      <select onChange={(e) => setCompany(e.target.value)}>
        <option value="">--Select--</option>
        <option value="Google">Google</option>
        <option value="Amazon">Amazon</option>
        <option value="Microsoft">Microsoft</option>
      </select>
    </div>
  );
}

export default CompanyDropdown;