import os
import uvicorn

if __name__ == "__main__":
    uvicorn.run("server:app", port=os.getenv("PORT", 5555))
