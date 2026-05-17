import { useState } from "react";

function ResumeUpload({ setResumeFile }) {
  const [fileName, setFileName] = useState("");

  const handleFileChange = (e) => {
    const file = e.target.files[0];

    if (!file) return;

    if (file.type !== "application/pdf") {
      alert("Please upload a PDF file only!");
      return;
    }

    setResumeFile(file);
    setFileName(file.name);
  };

  return (
    <div className="input-group">
      <h3>Upload Resume</h3>
      <input type="file" accept=".pdf" onChange={handleFileChange} />
      {fileName && <p className="footer-note">Selected: {fileName}</p>}
    </div>
  );
}

export default ResumeUpload;
