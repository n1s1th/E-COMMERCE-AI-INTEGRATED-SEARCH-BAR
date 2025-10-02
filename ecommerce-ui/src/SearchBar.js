import React, { useState } from "react";

function SearchBar({ onSearch }) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);

  // Fetch suggestions on input change
  const handleChange = async (e) => {
    const value = e.target.value;
    setQuery(value);
    if (value.length >= 2) {
      const resp = await fetch(`http://localhost:8000/autocomplete?q=${encodeURIComponent(value)}`);
      if (resp.ok) {
        const data = await resp.json();
        setSuggestions(data.suggestions);
      }
    } else {
      setSuggestions([]);
    }
  };

  // User clicks a suggestion
  const handleSuggestionClick = (s) => {
    setQuery(s);
    setSuggestions([]);
    onSearch(s);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setSuggestions([]);
    onSearch(query);
  };

  return (
    <form onSubmit={handleSubmit} style={{ position: "relative" }}>
      <input
        type="text"
        value={query}
        onChange={handleChange}
        placeholder="Search products..."
        autoComplete="off"
        style={{ padding: "0.5rem", width: "60%" }}
      />
      <button type="submit" style={{ padding: "0.5rem 1rem", marginLeft: "1rem" }}>
        Search
      </button>
      {/* Suggestion dropdown */}
      {suggestions.length > 0 && (
        <ul style={{
          position: "absolute",
          top: "2.5rem",
          left: 0,
          background: "#fff",
          border: "1px solid #ccc",
          width: "60%",
          zIndex: 10,
          listStyle: "none",
          margin: 0,
          padding: 0
        }}>
          {suggestions.map((s, i) => (
            <li
              key={i}
              style={{ padding: "0.5rem", cursor: "pointer" }}
              onClick={() => handleSuggestionClick(s)}
            >{s}</li>
          ))}
        </ul>
      )}
    </form>
  );
}

export default SearchBar;