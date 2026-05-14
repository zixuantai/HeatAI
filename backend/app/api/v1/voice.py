import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.core.dependencies import CurrentUser
from app.schemas.voice import VoiceASRRequest, VoiceTTSRequest
from app.services.chat import voice_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["语音"])


@router.post("/asr")
async def voice_asr(
    req: VoiceASRRequest,
    current_user: CurrentUser
):
    try:
        text = await voice_service.speech_to_text(req.audio)
        return {
            "code": 0,
            "message": "success",
            "data": {"text": text}
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"[Voice ASR] 未知错误: {e}")
        raise HTTPException(status_code=500, detail=f"语音识别服务异常: {str(e)}")


@router.post("/tts/stream")
async def voice_tts_stream(
    req: VoiceTTSRequest,
    current_user: CurrentUser
):
    logger.info(f"[Voice TTS] 收到流式合成请求, 文本: {req.text[:50]}...")

    async def event_generator():
        try:
            async for audio_chunk_b64 in voice_service.text_to_speech_stream(req.text):
                yield f"data: {json.dumps({'audio': audio_chunk_b64})}\n\n"
            yield "data: [DONE]\n\n"
        except ValueError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        except RuntimeError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        except Exception as e:
            logger.error(f"[Voice TTS] 流式合成异常: {e}")
            yield f"data: {json.dumps({'error': f'语音合成服务异常: {str(e)}'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )