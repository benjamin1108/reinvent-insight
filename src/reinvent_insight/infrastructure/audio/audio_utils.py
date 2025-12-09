"""
音频处理工具

提供 WAV 文件组装、Base64 解码等音频处理功能
"""

import base64
import struct
import logging
from typing import List

logger = logging.getLogger(__name__)


def decode_base64_pcm(base64_data: str) -> bytes:
    """
    解码 Base64 编码的 PCM 音频数据
    
    Args:
        base64_data: Base64 编码的字符串
        
    Returns:
        解码后的字节数据
    """
    try:
        return base64.b64decode(base64_data)
    except Exception as e:
        logger.error(f"Base64 解码失败: {e}")
        raise ValueError(f"无效的 Base64 数据: {e}")


def assemble_wav(
    pcm_chunks: List[bytes],
    sample_rate: int = 24000,
    channels: int = 1,
    bits_per_sample: int = 16
) -> bytes:
    """
    将 PCM 音频块组装成 WAV 文件
    
    WAV 文件格式:
    - RIFF header (12 bytes)
    - fmt chunk (24 bytes)
    - data chunk (8 bytes + PCM data)
    
    Args:
        pcm_chunks: PCM 数据块列表
        sample_rate: 采样率（Hz），默认 24000
        channels: 声道数，默认 1（单声道）
        bits_per_sample: 每样本位数，默认 16
        
    Returns:
        完整的 WAV 文件字节数据
    """
    # 拼接所有 PCM 数据
    pcm_data = b''.join(pcm_chunks)
    pcm_size = len(pcm_data)
    
    # 计算参数
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    
    # 构建 WAV 头
    # RIFF header
    riff_header = struct.pack(
        '<4sI4s',
        b'RIFF',                    # ChunkID
        36 + pcm_size,              # ChunkSize (文件大小 - 8)
        b'WAVE'                     # Format
    )
    
    # fmt chunk
    fmt_chunk = struct.pack(
        '<4sIHHIIHH',
        b'fmt ',                    # Subchunk1ID
        16,                         # Subchunk1Size (PCM 格式固定为 16)
        1,                          # AudioFormat (1 = PCM)
        channels,                   # NumChannels
        sample_rate,                # SampleRate
        byte_rate,                  # ByteRate
        block_align,                # BlockAlign
        bits_per_sample             # BitsPerSample
    )
    
    # data chunk
    data_chunk = struct.pack(
        '<4sI',
        b'data',                    # Subchunk2ID
        pcm_size                    # Subchunk2Size
    )
    
    # 组装完整的 WAV 文件
    wav_data = riff_header + fmt_chunk + data_chunk + pcm_data
    
    logger.info(
        f"WAV 文件组装完成: "
        f"大小={len(wav_data)} bytes, "
        f"采样率={sample_rate}Hz, "
        f"声道={channels}, "
        f"位深={bits_per_sample}bit"
    )
    
    return wav_data


def calculate_audio_duration(
    pcm_size: int,
    sample_rate: int = 24000,
    channels: int = 1,
    bits_per_sample: int = 16
) -> float:
    """
    计算音频时长
    
    Args:
        pcm_size: PCM 数据大小（字节）
        sample_rate: 采样率（Hz）
        channels: 声道数
        bits_per_sample: 每样本位数
        
    Returns:
        音频时长（秒）
    """
    bytes_per_sample = bits_per_sample // 8
    total_samples = pcm_size // (channels * bytes_per_sample)
    duration = total_samples / sample_rate
    
    return duration
