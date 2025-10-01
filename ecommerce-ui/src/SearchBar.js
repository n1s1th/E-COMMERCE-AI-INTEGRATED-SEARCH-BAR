import React, { useState } from "react";

function SearchBar({ onSearch }) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    onSearch(query);
  };

  return (
    <form onSubmit={handleSubmit} style={{ marginBottom: "2rem" }}>
      <input
        type="text"
        placeholder="Search products..."
        value={query}
        onChange={e => setQuery(e.target.value)}
        style={{ padding: "0.5rem", width: "60%" }}
      />
      <button type="submit" style={{ padding: "0.5rem 1rem", marginLeft: "1rem" }}>
        Search
      </button>
    </form>
  );
}

export default SearchBar;