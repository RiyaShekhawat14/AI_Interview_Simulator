function RoleInput({ role, setRole }) {
  return (
    <div>
      <h3>Enter Role</h3>

      <input
        type="text"
        placeholder="Data Scientist"
        value={role}
        onChange={(e) => setRole(e.target.value)}
        style={{ padding: "8px", width: "100%" }}
      />
    </div>
  );
}

export default RoleInput;
