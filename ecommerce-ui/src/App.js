import React, { useState } from "react";
import SearchBar from "./SearchBar";
import ProductList from "./ProductList";

function App() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (query) => {
    setLoading(true);
    const resp = await fetch(`http://localhost:8000/search?q=${encodeURIComponent(query)}`);
    const data = await resp.json();
    setProducts(data.items || []);
    setLoading(false);
  };

  return (
    <div style={{ maxWidth: 600, margin: "2rem auto", fontFamily: "Arial, sans-serif" }}>
      <h1>E-commerce AI Search</h1>
      <SearchBar onSearch={handleSearch} />
      {loading ? <div>Loading...</div> : <ProductList items={products} />}
    </div>
  );
}

export default App;