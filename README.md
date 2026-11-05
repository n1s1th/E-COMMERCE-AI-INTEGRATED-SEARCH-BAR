# E-COMMERCE-AI-INTEGRATED-SEARCH-BAR

An AI-powered search bar for e-commerce, built with Python (FastAPI + Whoosh) and a React.js frontend.  
Supports fuzzy search, autocomplete, filtering, and product cards from your catalog.

---

## 📁 File Structure

```
E-COMMERCE-AI-INTEGRATED-SEARCH-BAR/
├── app/                     # FastAPI app (main.py: API endpoints)
│   └── main.py
├── search/                  # Search logic and Whoosh indexer
│   ├── __init__.py
│   ├── indexer.py           # Index builder from products.json
│   └── searcher.py          # Search and autocomplete engine
├── data/
│   └── products.json        # Your product catalog data
├── requirements.txt         # Python backend dependencies
├── ecommerce-ui/            # React frontend (Create React App)
│   ├── public/
│   ├── src/
│   │   ├── App.js
│   │   ├── SearchBar.js
│   │   ├── ProductList.js
│   │   └── index.js
│   ├── package.json
│   └── ...
└── README.md
```

---

## 🚀 Backend Setup

1. **Clone the repo and create a virtual environment:**

   ```bash
   git clone https://github.com/n1s1th/E-COMMERCE-AI-INTEGRATED-SEARCH-BAR.git
   cd E-COMMERCE-AI-INTEGRATED-SEARCH-BAR
   python -m venv env
   source env/bin/activate   # or .\env\Scripts\activate on Windows
   ```

2. **Install backend dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Build the Whoosh index from your products:**

   ```bash
   python -m search.indexer --data data/products.json --index indexdir
   ```

4. **Start the FastAPI server:**

   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

   The API will be available at [http://localhost:8000](http://localhost:8000)  
   Docs at [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 💻 Frontend Setup

1. **Install frontend dependencies (in the `ui` directory):**

   ```bash
   cd ecommerce-ui
   npm install
   ```

2. **Start the React frontend:**

   ```bash
   npm start
   ```

   The UI will run at [http://localhost:3000](http://localhost:3000)

---

## 🔗 Connecting Backend & Frontend

- **CORS must be enabled** in FastAPI (`app/main.py`) for `http://localhost:3000` (already shown in backend code).
- The React app fetches from `http://localhost:8000/search` and `/autocomplete`.

---

## 📝 Usage

- Use the search bar on the frontend to search products by name, category, attributes, etc.
- Results are displayed as product cards.
- Autocomplete suggestions appear as you type.
- Supports filtering by brand, category, color, size, price, and stock status (see API docs for query parameters).

---

## 🛠️ API Endpoints

- `GET /search` — Search products (with filters, pagination, fuzzy matching)
- `GET /autocomplete` — Get autocomplete suggestions

See interactive docs at `/docs` for details.

---

## 📦 Requirements

**Backend:**
- Python 3.9+
- fastapi
- uvicorn
- whoosh
- pydantic

**Frontend:**
- Node.js 16+
- React (Create React App or Next.js)

---

## 🤖 Customization

- Add more product fields in `data/products.json` and update `search/indexer.py` schema.
- Tweak search relevance in `search/searcher.py`.
- Customize UI in `ecommerce-ui/src/`.

---

## 🏁 License

MIT

---

## 🙏 Credits

Built by [n1s1th](https://github.com/n1s1th)  
Powered by FastAPI, Whoosh, and React.
