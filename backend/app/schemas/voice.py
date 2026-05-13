from pydantic import BaseModel, Field


class VoiceASRRequest(BaseModel):
    audio: str = Field(..., min_length=1, description="Base64编码的WAV音频数据")


class VoiceTTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="需要合成的文本")


class ASRResponse(BaseModel):
    text: str


class TTSChunkResponse(BaseModel):
    audio: str = Field(..., description="Base64编码的音频片段")