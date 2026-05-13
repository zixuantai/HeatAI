import base64
import logging
import os
import tempfile
import asyncio
import queue
import threading
from typing import AsyncGenerator, Optional

import dashscope
from dashscope.audio.asr import Recognition, RecognitionResult
from dashscope.audio.tts_v2 import SpeechSynthesizer, AudioFormat, ResultCallback
from app.core.config import settings

logger = logging.getLogger(__name__)


class TTSCallback(ResultCallback):
    def __init__(self):
        super().__init__()
        self.audio_queue: queue.Queue = queue.Queue()
        self.error: Optional[str] = None
        self.done = threading.Event()

    def on_data(self, data: bytes) -> None:
        self.audio_queue.put(data)

    def on_complete(self) -> None:
        self.done.set()

    def on_error(self, message) -> None:
        self.error = str(message)
        self.done.set()

    def on_close(self) -> None:
        self.done.set()


class VoiceService:

    @staticmethod
    def _ensure_api_key():
        dashscope.api_key = settings.DASHSCOPE_API_KEY

    @staticmethod
    async def speech_to_text(audio_base64: str) -> str:
        VoiceService._ensure_api_key()

        audio_data = base64.b64decode(audio_base64)

        fd, temp_path = tempfile.mkstemp(suffix='.wav')
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(audio_data)

            logger.info(f"[ASR] 开始识别, 音频大小: {len(audio_data)} bytes")

            recognition = Recognition(
                model='paraformer-realtime-v2',
                callback=None,
                format='wav',
                sample_rate=16000
            )
            result = recognition.call(file=temp_path)

            logger.info(f"[ASR] status_code={result.status_code}, output={result.output}")

            if result.status_code != 200:
                error_msg = result.message or "语音识别失败"
                logger.error(f"[ASR] 识别失败: status={result.status_code}, msg={error_msg}")
                raise RuntimeError(f"语音识别失败: {error_msg}")

            sentence = result.get_sentence()
            logger.info(f"[ASR] get_sentence() = {sentence}, type={type(sentence).__name__}")
            if sentence is None:
                logger.warning("[ASR] 识别结果为空")
                return ""

            if isinstance(sentence, dict):
                text = sentence.get('text', '')
            elif isinstance(sentence, list):
                parts = []
                for s in sentence:
                    if isinstance(s, dict):
                        t = s.get('text', '')
                        if t:
                            parts.append(t)
                    else:
                        parts.append(str(s))
                text = ''.join(parts)
            else:
                text = str(sentence)

            logger.info(f"[ASR] 识别结果: {text}")
            return text.strip()

        except Exception as e:
            logger.error(f"[ASR] 识别异常: {e}")
            raise RuntimeError(f"语音识别失败: {str(e)}")
        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass

    @staticmethod
    async def text_to_speech_stream(text: str) -> AsyncGenerator[str, None]:
        VoiceService._ensure_api_key()

        logger.info(f"[TTS] 开始合成, 文本长度: {len(text)}")

        try:
            loop = asyncio.get_running_loop()
            callback = TTSCallback()
            synthesizer = SpeechSynthesizer(
                model='cosyvoice-v1',
                voice='longxiaochun',
                format=AudioFormat.WAV_16000HZ_MONO_16BIT,
                callback=callback
            )

            def _synthesize():
                try:
                    synthesizer.call(text)
                except Exception as ex:
                    callback.error = str(ex)
                    callback.done.set()

            thread = threading.Thread(target=_synthesize, daemon=True)
            thread.start()

            while not callback.done.is_set() or not callback.audio_queue.empty():
                try:
                    chunk = await loop.run_in_executor(
                        None,
                        lambda: callback.audio_queue.get(timeout=0.3)
                    )
                    chunk_b64 = base64.b64encode(chunk).decode('utf-8')
                    yield chunk_b64
                except queue.Empty:
                    if callback.done.is_set():
                        break
                    continue

            thread.join(timeout=5)

            if callback.error:
                logger.error(f"[TTS] 合成错误: {callback.error}")
                raise RuntimeError(f"语音合成失败: {callback.error}")

            logger.info(f"[TTS] 合成完成")

        except Exception as e:
            logger.error(f"[TTS] 合成异常: {e}")
            raise RuntimeError(f"语音合成失败: {str(e)}")


voice_service = VoiceService()