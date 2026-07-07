# RAG Sprint 1 – מנוע חיפוש סמנטי (Semantic Search)

פרויקט זה בונה את שכבת ה־**Retrieval** של מערכת RAG מעל מסמך PDF בעברית:
המדריך "מדריך לרוכש דירה". המטרה היא ליצור בסיס ידע שניתן לחפש בו לפי **משמעות**
(ולא לפי מילים מדויקות), באמצעות Embeddings ומסד נתונים וקטורי.

## מה זה RAG ומה זה Retrieval?

- **RAG** (Retrieval-Augmented Generation) = שיטה שבה לפני שמודל שפה עונה על שאלה,
  שולפים מתוך בסיס ידע את קטעי הטקסט הרלוונטיים ביותר ומצרפים אותם לשאלה.
- **Retrieval** = שלב השליפה בלבד: בהינתן שאלה, למצוא את קטעי הטקסט הכי רלוונטיים.
  זה בדיוק מה שאנחנו בונים כאן (בלי שלב היצירה/Generation).

## הרעיון בקצרה (הצינור המלא)

1. **טעינת מסמך** – קוראים את ה־PDF וממירים אותו לטקסט.
2. **חלוקה ל־Chunks** – מפרקים את הטקסט הארוך לקטעים קטנים וחופפים.
3. **Embeddings** – ממירים כל chunk לוקטור מספרים (מודל `gemini-embedding-001`).
   טקסטים עם משמעות דומה מקבלים וקטורים קרובים במרחב.
4. **Vector Database (Pinecone)** – שומרים את כל הוקטורים במסד שיודע לחפש
   "מי הכי דומה" במהירות.
5. **Semantic Search** – ממירים את השאלה לוקטור, ומבקשים מ־Pinecone את הקטעים
   הכי קרובים (top-k).

## מבנה הפרויקט

```
RAG-system/
├── data/
│   └── apartment_buyer_guide.pdf   # המסמך שעליו עובדים
├── notebooks/
│   └── rag_semantic_search.ipynb   # הנוטבוק הראשי (נבנה בשלבים)
├── .env.example                    # תבנית למפתחות (מעתיקים ל-.env)
├── .gitignore
├── requirements.txt
└── README.md
```

## התקנה והרצה

1. יצירת סביבה וירטואלית והתקנת התלויות:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. יצירת מפתחות API:
   - **Gemini**: https://aistudio.google.com/apikey (מפתח חדש נוצר אוטומטית כ־auth key).
   - **Pinecone**: https://app.pinecone.io (חשבון חינמי – Starter).

3. העתקת `.env.example` ל־`.env` ומילוי המפתחות האמיתיים:

```powershell
Copy-Item .env.example .env
```

> ⚠️ הקובץ `.env` מוגדר ב־`.gitignore` ולעולם לא נדחף ל־GitHub.

4. פתיחת הנוטבוק `notebooks/rag_semantic_search.ipynb` והרצת התאים לפי הסדר.

## טכנולוגיות

| רכיב | טכנולוגיה |
|------|-----------|
| Embeddings | Google Gemini – `gemini-embedding-001` (SDK: `google-genai`) |
| Vector DB | Pinecone (Serverless) |
| קריאת PDF | `pypdf` |
| ניהול מפתחות | `python-dotenv` |
