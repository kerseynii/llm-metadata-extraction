# LLM-Driven Building Metadata Extraction

This project demonstrates how **Large Language Models (LLMs)** can be used to extract structured building metadata from **OpenStreetMap (OSM)** data.

The system retrieves building information through the **Overpass API**, sends raw OpenStreetMap tags to a **locally running LLM via Ollama**, and converts the data into structured building metadata such as:

- building name  
- address  
- building use  
- height  
- number of storeys  
- roof type  
- construction date  

The enriched results are exported as **GeoJSON**, enabling visualization and analysis in GIS software such as **QGIS, ArcGIS, or GeoPandas**.

---

# Workflow
OpenStreetMap
↓
Overpass API
↓
Python Data Pipeline
↓
LLM Metadata Extraction
↓
GeoJSON Export


---

# Key Features

- Retrieve building data using the **Overpass API**
- Extract structured building metadata using a **Large Language Model**
- Prevent hallucination by returning **"Information not found"** when data is missing
- Export enriched building data as **GeoJSON**
- Compatible with common **GIS software**

Extracted attributes include:

- Building name
- Address
- Building use
- Height
- Number of storeys
- Roof type
- Construction date
- Additional metadata from OSM tags

---

# Computational Design

To reduce computational workload and improve runtime performance, the current implementation processes **only the first 10 buildings retrieved from the bounding box**.

This limitation is implemented in the code as:

```python
first_10 = buildings[:10]

The system can easily be modified to process all buildings within the bounding box by replacing this line with:
first_10 = buildings

Install Ollama

Install Ollama:

https://ollama.com

Download the model:
ollama pull gemma3:4b

Environment Configuration

Create a .env file based on .env.example:

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b
OVERPASS_API_URL=http://overpass-api.de/api/interpreter

Run the Application
python main.py

The application will:
Fetch buildings from OpenStreetMap
Send building tags to the LLM
Extract structured metadata
Export the results as GeoJSON

**Output**
The processed dataset is exported as:
enriched_buildings_llm.geojson

This file can be opened in:

QGIS
ArcGIS
GeoPandas
Web mapping frameworks
