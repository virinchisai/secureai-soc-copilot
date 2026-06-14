from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings, get_settings
from app.core.database import Database
from app.dependencies import (
    get_current_user,
    get_database,
    get_rag_service,
    get_upload_storage,
)
from app.schemas import DeleteDocumentResponse, DocumentResponse, UploadResponse
from app.services.extraction import ALLOWED_EXTENSIONS, ExtractionError, extract_text
from app.services.rag import RAGService
from app.services.storage import UploadStorage


router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    current_user: str = Depends(get_current_user),
    database: Database = Depends(get_database),
) -> list[dict]:
    return database.list_documents(current_user)


@router.delete("/{document_id}", response_model=DeleteDocumentResponse)
async def delete_document(
    document_id: str,
    current_user: str = Depends(get_current_user),
    database: Database = Depends(get_database),
    rag_service: RAGService = Depends(get_rag_service),
    upload_storage: UploadStorage = Depends(get_upload_storage),
) -> DeleteDocumentResponse:
    document = database.get_document(document_id, current_user)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    vector_ids = [
        f"{document_id}:{chunk_number}"
        for chunk_number in range(1, document["chunk_count"] + 1)
    ]
    try:
        await run_in_threadpool(
            rag_service.delete_vectors,
            current_user,
            vector_ids,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Document vectors could not be removed.",
        ) from exc

    await run_in_threadpool(
        upload_storage.delete_document,
        current_user,
        document_id,
    )
    database.delete_document(document_id, current_user)
    return DeleteDocumentResponse(
        document_id=document_id,
        filename=document["filename"],
        message="Document removed successfully",
    )


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
    database: Database = Depends(get_database),
    rag_service: RAGService = Depends(get_rag_service),
    upload_storage: UploadStorage = Depends(get_upload_storage),
    settings: Settings = Depends(get_settings),
) -> UploadResponse:
    filename = Path(file.filename or "upload").name
    if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only .txt, .log, and .pdf files are supported",
        )

    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_mb} MB limit",
        )

    document_id = str(uuid4())
    stored_upload = None
    ingested = None
    try:
        pages = extract_text(filename, content)
        stored_upload = await run_in_threadpool(
            upload_storage.save,
            current_user,
            document_id,
            filename,
            content,
        )
        ingested = await run_in_threadpool(
            rag_service.ingest,
            current_user,
            document_id,
            filename,
            pages,
        )
    except ExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        if stored_upload is not None:
            await run_in_threadpool(
                upload_storage.delete_document,
                current_user,
                document_id,
            )
        raise HTTPException(
            status_code=502,
            detail="Document indexing failed. Check the embedding provider configuration.",
        ) from exc

    try:
        database.add_document(
            document_id=ingested.document_id,
            user_id=current_user,
            filename=filename,
            chunk_count=ingested.chunk_count,
            size_bytes=stored_upload.size_bytes,
            sha256=stored_upload.sha256,
            stored_path=stored_upload.relative_path,
        )
    except Exception:
        if ingested is not None:
            await run_in_threadpool(
                rag_service.delete_vectors,
                current_user,
                ingested.vector_ids,
            )
        await run_in_threadpool(
            upload_storage.delete_document,
            current_user,
            document_id,
        )
        raise

    document = next(
        item
        for item in database.list_documents(current_user)
        if item["id"] == document_id
    )
    return UploadResponse(
        document=DocumentResponse(**document),
        message="Document indexed successfully",
    )
