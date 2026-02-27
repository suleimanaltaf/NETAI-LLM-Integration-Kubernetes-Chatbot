"""Chat API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from netai_chatbot.api.models import (
    ChatRequest,
    ChatResponse,
    ConversationInfo,
    MessageInfo,
    StreamChatRequest,
)
from netai_chatbot.llm.client import ChatMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def _get_app_state():
    """Lazy import to avoid circular dependency."""
    from netai_chatbot.main import app_state
    return app_state


@router.post("", response_model=ChatResponse)
async def send_message(request: ChatRequest) -> ChatResponse:
    """Send a message to the NETAI chatbot and receive a response.

    If conversation_id is provided, continues the existing conversation.
    Otherwise, creates a new conversation.
    """
    state = _get_app_state()

    # Get or create conversation
    if request.conversation_id:
        conv = await state.conversation_store.get_conversation(request.conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conversation_id = request.conversation_id
    else:
        conversation_id = await state.conversation_store.create_conversation()

    # Build context-aware system prompt
    if request.include_context:
        telemetry_ctx, anomaly_ctx = await state.context_builder.build_full_context(
            request.message
        )
        system_prompt = state.prompt_builder.build_system_prompt(
            telemetry_context=telemetry_ctx,
            anomaly_context=anomaly_ctx,
        )
    else:
        system_prompt = state.prompt_builder.build_system_prompt()

    # Build message history
    history = await state.conversation_store.get_messages(conversation_id, limit=20)
    messages: list[ChatMessage] = [ChatMessage(role="system", content=system_prompt)]

    # Add few-shot examples for new conversations
    if not history:
        for ex in state.prompt_builder.get_few_shot_messages():
            messages.append(ChatMessage(role=ex["role"], content=ex["content"]))

    # Add conversation history
    for msg in history:
        messages.append(ChatMessage(role=msg["role"], content=msg["content"]))

    # Add current user message
    messages.append(ChatMessage(role="user", content=request.message))

    # Save user message
    await state.conversation_store.add_message(
        conversation_id, "user", request.message
    )

    # Get LLM response
    try:
        response = await state.llm_client.chat(
            messages=messages,
            model=request.model,
        )
    except Exception as e:
        logger.error("LLM request failed: %s", e)
        raise HTTPException(status_code=502, detail=f"LLM service error: {e}")

    # Save assistant response
    await state.conversation_store.add_message(
        conversation_id, "assistant", response.content,
        metadata={"model": response.model, "usage": response.usage},
    )

    return ChatResponse(
        conversation_id=conversation_id,
        message=response.content,
        model=response.model,
        usage=response.usage,
    )


@router.post("/stream")
async def stream_message(request: StreamChatRequest):
    """Stream a chat response using Server-Sent Events."""
    state = _get_app_state()

    # Get or create conversation
    if request.conversation_id:
        conv = await state.conversation_store.get_conversation(request.conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conversation_id = request.conversation_id
    else:
        conversation_id = await state.conversation_store.create_conversation()

    # Build system prompt
    if request.include_context:
        telemetry_ctx, anomaly_ctx = await state.context_builder.build_full_context(
            request.message
        )
        system_prompt = state.prompt_builder.build_system_prompt(
            telemetry_context=telemetry_ctx,
            anomaly_context=anomaly_ctx,
        )
    else:
        system_prompt = state.prompt_builder.build_system_prompt()

    # Build messages
    history = await state.conversation_store.get_messages(conversation_id, limit=20)
    messages: list[ChatMessage] = [ChatMessage(role="system", content=system_prompt)]
    for msg in history:
        messages.append(ChatMessage(role=msg["role"], content=msg["content"]))
    messages.append(ChatMessage(role="user", content=request.message))

    # Save user message
    await state.conversation_store.add_message(
        conversation_id, "user", request.message
    )

    async def event_generator():
        full_response = []
        try:
            async for chunk in state.llm_client.chat_stream(
                messages=messages, model=request.model
            ):
                full_response.append(chunk)
                yield f"data: {chunk}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {e}\n\n"
        finally:
            # Save complete response
            content = "".join(full_response)
            if content.strip():
                await state.conversation_store.add_message(
                    conversation_id, "assistant", content
                )
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Conversation-Id": conversation_id,
        },
    )


@router.get("/conversations", response_model=list[ConversationInfo])
async def list_conversations():
    """List recent conversations."""
    state = _get_app_state()
    convs = await state.conversation_store.list_conversations()
    return [ConversationInfo(**c) for c in convs]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageInfo])
async def get_conversation_messages(conversation_id: str):
    """Get all messages in a conversation."""
    state = _get_app_state()
    conv = await state.conversation_store.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await state.conversation_store.get_messages(conversation_id)
    return [MessageInfo(**m) for m in messages]


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages."""
    state = _get_app_state()
    conv = await state.conversation_store.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await state.conversation_store.delete_conversation(conversation_id)
    return {"status": "deleted"}
