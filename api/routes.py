from fastapi import APIRouter, HTTPException, Query, Request, BackgroundTasks
from pydantic import BaseModel
from services.ip_utils import get_client_ip
from services.db_logger import log_query
from services.embedder import build_faiss_index
from services.retriever import retrieve_chunks
from services.llm_service import query_gemini,query_openai
from Extraction_Models import parse_document_url, parse_document_file
from threading import Lock
import hashlib, time
from concurrent.futures import ThreadPoolExecutor

router = APIRouter()

class QueryRequest(BaseModel):
    url: str
    questions: list[str]

class LocalQueryRequest(BaseModel):
    document_path: str
    questions: list[str]

def get_document_id(url: str):
    return hashlib.md5(url.encode()).hexdigest()

doc_cache = {}
doc_cache_lock = Lock()

@router.delete("/cache/clear")
async def clear_cache(doc_id: str = Query(None), url: str = Query(None), doc_only: bool = Query(False)):
    cleared = {}
    if url:
        doc_id = get_document_id(url)
    if doc_id:
        with doc_cache_lock:
            if doc_id in doc_cache:
                del doc_cache[doc_id]
                cleared["doc_cache"] = f"Cleared document {doc_id}"
    else:
        with doc_cache_lock:
            doc_cache.clear()
            cleared["doc_cache"] = "Cleared ALL documents"
    return {"status": "success", "cleared": cleared}

def print_timings(timings: dict):
    print("\n=== TIMINGS ===")
    for k, v in timings.items():
        if isinstance(v, float):
            print(f"[TIMER] {k}: {v:.4f}s")
        elif isinstance(v, list):
            print(f"[TIMER] {k}: {', '.join(f'{x:.4f}s' for x in v)}")
        else:
            print(f"[TIMER] {k}: {v}")
    print("================\n")

@router.post("/hackrx/run")
async def run_query(request: QueryRequest, fastapi_request: Request, background_tasks: BackgroundTasks):
    timings = {}
    try:
        user_ip = get_client_ip(fastapi_request)
        user_agent = fastapi_request.headers.get("user-agent", "Unknown")
        doc_id = get_document_id(request.url)
        print("Input :",request.url,request.questions)
        # Parsing
        t_parse_start = time.time()
        with doc_cache_lock:
            if doc_id in doc_cache:
                cached = doc_cache[doc_id]
                text_chunks, index, texts = cached["chunks"], cached["index"], cached["texts"]
                timings["parse_time"] = 0
                timings["index_time"] = 0
            else:
                text_chunks = parse_document_url(request.url)
                t_parse_end = time.time()
                timings["parse_time"] = t_parse_end - t_parse_start

                # Indexing
                t_index_start = time.time()
                index, texts = build_faiss_index(text_chunks)
                t_index_end = time.time()
                timings["index_time"] = t_index_end - t_index_start

                doc_cache[doc_id] = {"chunks": text_chunks, "index": index, "texts": texts}
        timings["cache_check_time"] = time.time() - t_parse_start

        # Retrieval
        t_retrieve_start = time.time()
        all_chunks = set()
        for question in request.questions:
            all_chunks.update(retrieve_chunks(index, texts, question))
        context_chunks = list(all_chunks)
        timings["retrieval_time"] = time.time() - t_retrieve_start

        # LLM query
        t_llm_start = time.time()
        batch_size = 10
        results_dict = {}
        llm_batch_timings = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(0, len(request.questions), batch_size):
                batch = request.questions[i:i + batch_size]
                futures.append(executor.submit(query_openai, batch, context_chunks))
            for i, future in enumerate(futures):
                t_batch_start = time.time()
                result = future.result()
                t_batch_end = time.time()
                llm_batch_timings.append(t_batch_end - t_batch_start)
                if "answers" in result:
                    for j, ans in enumerate(result["answers"]):
                        results_dict[i * batch_size + j] = ans
        timings["llm_time"] = time.time() - t_llm_start
        timings["llm_batch_times"] = llm_batch_timings

        responses = [results_dict.get(i, "Not Found") for i in range(len(request.questions))]

        # Logging
        total_float_time = sum(v for v in timings.values() if isinstance(v, (int, float)))
        for q, a in zip(request.questions, responses):
            background_tasks.add_task(log_query, request.url, q, a, user_ip, total_float_time, user_agent)

        # Print timings in console
        print_timings(timings)

        # Return ONLY answers
        return {"answers": responses}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.post("/hackrx/local")
async def run_local_query(request: LocalQueryRequest, fastapi_request: Request, background_tasks: BackgroundTasks):
    timings = {}
    try:
        user_ip = get_client_ip(fastapi_request)
        user_agent = fastapi_request.headers.get("user-agent", "Unknown")

        # Parsing
        t_parse_start = time.time()
        text_chunks = parse_document_file(request.document_path)
        t_parse_end = time.time()
        timings["parse_time"] = t_parse_end - t_parse_start

        # Indexing
        t_index_start = time.time()
        index, texts = build_faiss_index(text_chunks)
        t_index_end = time.time()
        timings["index_time"] = t_index_end - t_index_start

        # Retrieval
        t_retrieve_start = time.time()
        all_chunks = set()
        for question in request.questions:
            all_chunks.update(retrieve_chunks(index, texts, question))
        context_chunks = list(all_chunks)
        timings["retrieval_time"] = time.time() - t_retrieve_start

        # LLM query
        t_llm_start = time.time()
        batch_size = 20
        results_dict = {}
        llm_batch_timings = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(0, len(request.questions), batch_size):
                batch = request.questions[i:i + batch_size]
                futures.append(executor.submit(query_gemini, batch, context_chunks))
            for i, future in enumerate(futures):
                t_batch_start = time.time()
                result = future.result()
                t_batch_end = time.time()
                llm_batch_timings.append(t_batch_end - t_batch_start)
                if "answers" in result:
                    for j, ans in enumerate(result["answers"]):
                        results_dict[i * batch_size + j] = ans
        timings["llm_time"] = time.time() - t_llm_start
        timings["llm_batch_times"] = llm_batch_timings

        responses = [results_dict.get(i, "Not Found") for i in range(len(request.questions))]

        # Logging
        total_float_time = sum(v for v in timings.values() if isinstance(v, (int, float)))
        for q, a in zip(request.questions, responses):
            background_tasks.add_task(log_query, request.document_path, q, a, user_ip, total_float_time, user_agent)

        # Print timings in console
        print_timings(timings)

        # Return ONLY answers
        return {"answers": responses}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
    



@router.post("/hackrx/run_openai")
async def run_query_openai(request: QueryRequest, fastapi_request: Request, background_tasks: BackgroundTasks):
    timings = {}
    try:
        user_ip = get_client_ip(fastapi_request)
        user_agent = fastapi_request.headers.get("user-agent", "Unknown")
        doc_id = get_document_id(request.url)

        # Parsing
        t_parse_start = time.time()
        with doc_cache_lock:
            if doc_id in doc_cache:
                cached = doc_cache[doc_id]
                text_chunks, index, texts = cached["chunks"], cached["index"], cached["texts"]
                timings["parse_time"] = 0
                timings["index_time"] = 0
            else:
                text_chunks = parse_document_url(request.url)
                t_parse_end = time.time()
                timings["parse_time"] = t_parse_end - t_parse_start

                # Indexing
                t_index_start = time.time()
                index, texts = build_faiss_index(text_chunks)
                t_index_end = time.time()
                timings["index_time"] = t_index_end - t_index_start

                doc_cache[doc_id] = {"chunks": text_chunks, "index": index, "texts": texts}
        timings["cache_check_time"] = time.time() - t_parse_start

        # Retrieval
        t_retrieve_start = time.time()
        all_chunks = set()
        for question in request.questions:
            all_chunks.update(retrieve_chunks(index, texts, question))
        context_chunks = list(all_chunks)
        timings["retrieval_time"] = time.time() - t_retrieve_start

        # OpenAI LLM query
        t_llm_start = time.time()
        batch_size = 10
        results_dict = {}
        llm_batch_timings = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(0, len(request.questions), batch_size):
                batch = request.questions[i:i + batch_size]
                futures.append(executor.submit(query_gemini, batch, context_chunks))
            for i, future in enumerate(futures):
                t_batch_start = time.time()
                result = future.result()
                t_batch_end = time.time()
                llm_batch_timings.append(t_batch_end - t_batch_start)
                if "answers" in result:
                    for j, ans in enumerate(result["answers"]):
                        results_dict[i * batch_size + j] = ans
        timings["llm_time"] = time.time() - t_llm_start
        timings["llm_batch_times"] = llm_batch_timings

        responses = [results_dict.get(i, "Not Found") for i in range(len(request.questions))]

        # Logging
        total_float_time = sum(v for v in timings.values() if isinstance(v, (int, float)))
        for q, a in zip(request.questions, responses):
            background_tasks.add_task(log_query, request.url, q, a, user_ip, total_float_time, user_agent)

        # Print timings in console
        print_timings(timings)

        return {"answers": responses}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

