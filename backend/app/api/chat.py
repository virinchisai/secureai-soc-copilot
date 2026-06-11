from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from app.core.database import Database
from app.dependencies import get_current_user, get_database, get_rag_service
from app.schemas import AnswerResponse, QuestionRequest
from app.services.guard import detect_prompt_injection
from app.services.rag import RAGService


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/ask", response_model=AnswerResponse)
async def ask_question(
    request: QuestionRequest,
    current_user: str = Depends(get_current_user),
    database: Database = Depends(get_database),
    rag_service: RAGService = Depends(get_rag_service),
) -> AnswerResponse:
    guard_message = detect_prompt_injection(request.question)
    if guard_message:
        database.add_audit_log(
            user_id=current_user,
            question=request.question,
            status="blocked_prompt_injection",
        )
        raise HTTPException(status_code=400, detail=guard_message)

    try:
        answer, sources, provider, model = await run_in_threadpool(
            rag_service.answer,
            current_user,
            request.question,
        )
    except Exception as exc:
        database.add_audit_log(
            user_id=current_user,
            question=request.question,
            status="provider_error",
        )
        raise HTTPException(
            status_code=502,
            detail="Answer generation failed. Check the model provider configuration.",
        ) from exc

    database.add_audit_log(
        user_id=current_user,
        question=request.question,
        status="answered" if sources else "no_sources",
        source_count=len(sources),
    )
    return AnswerResponse(
        answer=answer,
        sources=sources,
        provider=provider,
        model=model,
    )
