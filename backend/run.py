import os
import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"Starting Nutrition & Energy Coach Backend on http://localhost:{port}")
    print(f"Swagger API Docs available at http://localhost:{port}/docs")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
