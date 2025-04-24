
from flask import Flask, request, jsonify, render_template
import pandas as pd
import google.generativeai as genai

app = Flask(__name__)

# Load CSV and preprocess
df = pd.read_csv("packaging_oee_data.csv")
df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')

# Gemini API config
api_key = ""  # 🔑 Replace with your actual Gemini API key
genai.configure(api_key=api_key)
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

# Calculate OEE
def calculate_oee(row):
    availability = row['Operating Time'] / row['Planned Time']
    performance = (row['Ideal Cycle Time'] * row['Total Count']) / (row['Operating Time'] * 60)
    quality = row['Good Count'] / row['Total Count']
    return round(availability * performance * quality * 100, 2)

# Homepage (optional ChatGPT-style UI hook)
@app.route("/")
def index():
    return render_template("index.html")  # Template can be added later

# Endpoint to handle user queries
@app.route("/query", methods=["POST"])
def query():
    user_query = request.json.get("query", "")

    prompt = f"""
    You are a smart data assistant. From this user query, extract these fields:

    Device ID: (e.g., PKG001)
    Location: (e.g., Plant A)
    Month: (e.g., March)
    Year: (e.g., 2025)

    Query: "{user_query}"

    Return the result in the following format:
    Device ID: ...
    Location: ...
    Month: ...
    Year: ...
    """

    try:
        response = model.generate_content(prompt)
        text = response.text
        lines = text.splitlines()
        filters = {line.split(":")[0].strip(): line.split(":")[1].strip() for line in lines if ":" in line}

        device = filters.get("Device ID")
        location = filters.get("Location")
        month = filters.get("Month")
        year = filters.get("Year")

        if not all([device, location, month, year]):
            raise ValueError("Missing fields in the extracted query.")

        # Filter the DataFrame with normalized values
        filtered = df[
            (df["Device ID"].str.strip().str.upper() == device.strip().upper()) &
            (df["Location"].str.strip().str.upper() == location.strip().upper()) &
            (df["Timestamp"].dt.month == pd.to_datetime(month, format='%B').month) &
            (df["Timestamp"].dt.year == int(year))
        ]

        if filtered.empty:
            return jsonify({"response": "❌ No data found for the specified query."})

        oee_scores = filtered.apply(calculate_oee, axis=1)
        avg_oee = round(oee_scores.mean(), 2)
        return jsonify({
            "response": f"✅ The average OEE for {device} at {location} in {month} {year} is {avg_oee}%."
        })

    except Exception as e:
        return jsonify({"response": f"❗ Error processing query: {str(e)}"})

if __name__ == "__main__":
    app.run(debug=True)
