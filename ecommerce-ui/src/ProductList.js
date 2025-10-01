import React from "react";

function ProductList({ items }) {
  if (!items.length) return <div>No products found.</div>;
  return (
    <div>
      {items.map(product => (
        <div key={product.id} style={{
          border: "1px solid #ccc",
          padding: "1rem",
          marginBottom: "1rem",
          borderRadius: "8px"
        }}>
          <img src={product.image} alt={product.product_name} style={{ width: 120, marginRight: 16 }} />
          <div>
            <h3>{product.product_name}</h3>
            <p><b>Price:</b> ₹{product.price}</p>
            <p><b>Sizes:</b> {product.sizes.join(", ")}</p>
            <p><b>Color:</b> {product.color}</p>
            <p><b>Brand:</b> {product.brand_slug}</p>
            <p><b>Category:</b> {product.category}</p>
            <p>
              <a href={product.pdp_url} target="_blank" rel="noopener noreferrer">View Product</a>
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

export default ProductList;