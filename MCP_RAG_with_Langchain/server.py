import os
import requests
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from PyPDF2 import PdfReader

from fastmcp import FastMCP


current_dir = Path(__file__).parent
CHROMA_PATH = os.path.join(current_dir,"chroma_db")
EMBED_MODEL = "nomic-embed-text"
OLLAMA_BASE_URL = "http://localhost:11434"
CHUNK_SIZE = 4096
CHUNK_OVERLAP = CHUNK_SIZE//10
COLLECTION_NAME = "documents"

mcp = FastMCP("langchain-vector-db")

embeddings = OllamaEmbeddings(model = EMBED_MODEL,
                              base_url=OLLAMA_BASE_URL)


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size = CHUNK_SIZE,
    chunk_overlap = CHUNK_OVERLAP,
    length_function = len,
    separators=["\n\n","\n"," ",""]
)

vectorstore = Chroma(
    persist_directory=CHROMA_PATH,
    embedding_function=embeddings,
    collection_name=COLLECTION_NAME
)

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using PyPDF2"""
    try:
        reader = PdfReader(pdf_path)
        text =""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text +=page_text + "\n"
        return text
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return ""
    
def process_single_pdf(pdf_path:str)-> int:
    """ Process a single PDF and add to vectorstore """
    text = extract_text_from_pdf(pdf_path)

    if not text:
        print(f"No text extracted from {pdf_path}")
        return 0
    
    doc = Document(page_content=text, 
                   metadata = {
                       "source":str(pdf_path),
                       "filename":Path(pdf_path).name
                   })
    chunks = text_splitter.split_documents([doc])

    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"]=i
        chunk.metadata["total_chunks"]=len(chunks)
    
    ids = [f"{Path(pdf_path).stem}_chunk_{i}" for i in range(len(chunks))]
    vectorstore.add_documents(documents=chunks, ids = ids)

    return len(chunks)

def download_pdf(url:str, download_dir:str = "./downloads")-> str:
    """Download PDF for URL"""
    os.makedirs(download_dir, exist_ok=True)
    filename = Path(url.split("?")[0]).name
    if not filename.endswith('.pdf'):
        filename = f"downloaded_{Path(url).stem}.pdf"
    
    local_path = os.path.join(download_dir,filename)

    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(local_path,'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return local_path

@mcp.tool()
async def ingest_pdf(source:str)->Dict[str,Any]:
    """
    Ingest PDF for folder, file path or URL
    
    Args:
        source: Can be:
            - Folder path: processes all PDFs in the folder
            - File path: processes file PDF
            - URL: downloads and processes PDF

    Returns:
        Status and number of chunks added
    """
    try:
        total_chunks = 0
        processed_files = []
        
        if source.startswith(('http://','https://')):
            print(f"Downloading PDF from {source}")
            local_path = download_pdf(source)
            chunks = process_single_pdf(local_path)
            total_chunks+=chunks
            processed_files.append(local_path)
            print(f"Processed {local_path}: {chunks} chunks")
        
        elif os.path.isdir(source):
            pdf_files = list(Path(source).glob("*.pdf"))
            print(f"Found {len(pdf_files)} PDF files in {source}")

            for pdf_file in pdf_files:
                print(f"Processing {pdf_file.name} ...")
                chunks = process_single_pdf(str(pdf_file))
                total_chunks+=chunks
                processed_files.append(str(pdf_file))
                print(f"Added {chunks} chunks from {pdf_file.name}")
        elif os.path.isfile(source) and source.endswith('.pdf'):
            print(f"Processing single file: {source}")
            chunks = process_single_pdf(source)
            total_chunks += chunks
            processed_files.append(source)
            print(f"Added {chunks} chunks")

        else:
            return {
                "status": "error",
                "message": f"Invalid source: {source}. Must be a PDF file, folder or a URL"
            }
        return {
            "status": "success",
            "chunks_added": total_chunks,
            "files_processed": len(processed_files),
            "files": processed_files
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    
@mcp.tool()
async def retrieve(query: str, n: int = 5) -> List[Dict[str, Any]]:
    """
        Retrieve top N chunks for a given query

        Args:
            query: Search query
            n: Number of chunks to retrieve
        Returns:
            Top N matching chunks with scores
    """
    try:
        results = vectorstore.similarity_search_with_score(query, k=n)

        chunks = []
        for doc, score in results:
            chunks.append({
                "text":doc.page_content,
                "metadata":doc.metadata,
                "similarity_score":float(1 - score),
                "distance": float(score)
            })
        return chunks
    except Exception as e:
        return [{"error":str(e)}]

@mcp.tool()
async def db_info()-> Dict[str, Any]:
    """
    Get ChromaDB and collection information

    Returns:
        Database and collection statistics
    """
    try:
        collection = vectorstore._collection
        count = collection.count()

        sample_size = min(100,count) if count>0 else 0
        sources = set()

        if sample_size>0:
            sample = collection.get(
                limit = sample_size,
                include=["metadatas"]
            )

            if sample["metadatas"]:
                for metadata in sample['metadatas']:
                    if metadata and 'source' in metadata:
                        sources.add(metadata['source'])
        
        return {
            "database_path":CHROMA_PATH,
            "collection_name":COLLECTION_NAME,
            "embedding_model": EMBED_MODEL,
            "ollama_base_url": OLLAMA_BASE_URL,
            "total_chunks": count,
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
            "unique_sources": list(sources),
            "num_sources": len(sources)
        }
    except Exception as e:
        return {
            "error":str(e)
        }

@mcp.tool()
async def clear_db()->Dict[str,Any]:
    """
    Clear all data from the database
    
    Returns:
        Confirmation message
    """
    try:
        global vectorstore

        vectorstore.delete_collection()

        vectorstore = Chroma(
            persist_directory = CHROMA_PATH,
            embedding_function = embeddings,
            collection_name = COLLECTION_NAME
        )

        return {
            "status":"success",
            "message":"Database cleared and reset"
        }
    except Exception as e:
        return {
            "status":"error",
            "message":str(e)
        }
    

def main():
    print("=" * 50)
    print("Langchain Chroma Vector DB Server")
    print("=" * 50)
    print(f"ChromaDB Path: {CHROMA_PATH}")
    print(f"Embedding Model: {EMBED_MODEL}")
    print(f"Ollama URL: {OLLAMA_BASE_URL}")
    print(f"Chunk Size: {CHUNK_SIZE}")
    print(f"Chunk Overlap: {CHUNK_OVERLAP}")
    print("-"*50)
    print("Available Tools:")
    print(" - ingest_pdf: Add PDFs to database")
    print(" - retrieve: Search for chunks")
    print(" - db_info: Get database info")
    print(" - clear_db: Clear entire database")
    print("=" * 50)


if __name__ == "__main__":
    main()
    mcp.run(transport="stdio")