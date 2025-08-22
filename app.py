import os
import warnings

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3" 
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import tensorflow as tf
tf.get_logger().setLevel("ERROR")
warnings.filterwarnings("ignore", module="tensorflow")

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.embedder import preload_model
import api.routes as routes
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting HackRx Insurance Policy Assistant...")
    print("⏳ Loading model...")
    preload_model()
    yield

app = FastAPI(title="HackRx Insurance Policy Assistant", version="3.2.6", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "HackRx Insurance Policy Assistant API is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
