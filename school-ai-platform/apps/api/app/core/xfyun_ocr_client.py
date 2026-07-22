"""
讯飞通用文档识别 OCR 客户端
支持 HTTP POST 方式，支持图片、PDF、DOCX 文件
"""
import asyncio
import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import ssl
import logging
from typing import Optional, Tuple

import websockets
import httpx

from app.core.config import settings
from app.core.file_processor import process_file_for_ocr, get_file_type

logger = logging.getLogger(__name__)


class XfyunOcrClient:
    """讯飞OCR客户端"""

    def __init__(self):
        self.appid = settings.XFYUN_APPID
        self.api_secret = settings.XFYUN_API_SECRET
        self.api_key = settings.XFYUN_API_KEY
        self.ocr_url = settings.XFYUN_OCR_URL

    def _generate_signature(self, date: str, host: str, path: str, method: str = "POST") -> str:
        """生成授权签名"""
        signature_origin = f"host: {host}\ndate: {date}\n{method} {path} HTTP/1.1"
        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        signature = base64.b64encode(signature_sha).decode("utf-8")

        authorization_origin = (
            f'api_key="{self.api_key}", '
            f'algorithm="hmac-sha256", '
            f'headers="host date request-line", '
            f'signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")

        return authorization

    def _build_auth_url(self, method: str = "POST", is_websocket: bool = False) -> str:
        """构建带签名的URL"""
        parsed_url = urllib.parse.urlparse(self.ocr_url)
        scheme = parsed_url.scheme
        host = parsed_url.hostname
        path = parsed_url.path
        port = parsed_url.port or (443 if scheme == "https" else 80)

        date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        authorization = self._generate_signature(date, host, path, method)

        params = {
            "authorization": authorization,
            "date": date,
            "host": host,
        }

        if is_websocket:
            ws_scheme = "wss" if scheme == "https" else "ws"
            return f"{ws_scheme}://{host}:{port}{path}?{urllib.parse.urlencode(params)}"
        else:
            return f"{scheme}://{host}:{port}{path}?{urllib.parse.urlencode(params)}"

    def _extract_text_from_response(self, response_data: dict) -> str:
        """从响应数据中提取文本"""
        try:
            if "payload" in response_data and "result" in response_data["payload"]:
                result = response_data["payload"]["result"]
                
                if "text" in result and result["text"]:
                    text_b64 = result["text"]
                    decoded_text = base64.b64decode(text_b64).decode("utf-8")
                    text_json = json.loads(decoded_text)
                    
                    return self._parse_text_json(text_json)
            
            logger.warning(f"OCR响应中未找到有效文本数据")
            return ""
        except Exception as e:
            logger.error(f"解析响应文本失败: {str(e)}", exc_info=True)
            return ""

    def _parse_text_json(self, data: dict) -> str:
        """解析文本JSON结构，提取所有文本内容（去重）"""
        seen = set()
        texts = []
        
        def extract(item):
            if isinstance(item, dict):
                if "text" in item:
                    text_val = item["text"]
                    if isinstance(text_val, list):
                        for t in text_val:
                            if isinstance(t, str) and t and t not in seen:
                                seen.add(t)
                                texts.append(t)
                    elif isinstance(text_val, str) and text_val and text_val not in seen:
                        seen.add(text_val)
                        texts.append(text_val)
                if "content" in item:
                    extract(item["content"])
                for key, val in item.items():
                    if key not in ["text", "content", "attribute", "coord", "contour", "angle", "score"]:
                        extract(val)
            elif isinstance(item, list):
                for sub_item in item:
                    extract(sub_item)
        
        extract(data)
        return "\n".join(texts)

    async def _recognize_single_image(self, image_path: str) -> Tuple[str, Optional[str]]:
        """
        使用 HTTP POST 方式调用讯飞OCR识别单张图片
        :param image_path: 图片文件路径
        :return: (识别文本, 置信度)
        """
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()

            image_base64 = base64.b64encode(image_data).decode("utf-8")
            logger.info(f"图片大小: {len(image_data)} bytes")

            full_url = self._build_auth_url("POST")

            payload = {
                "header": {
                    "app_id": self.appid,
                    "status": 0,
                },
                "parameter": {
                    "ocr": {
                        "result_option": "normal",
                        "result_format": "json",
                        "output_type": "one_shot",
                        "result": {
                            "encoding": "utf8",
                            "compress": "raw",
                            "format": "plain",
                        },
                    },
                },
                "payload": {
                    "image": {
                        "encoding": "png",
                        "image": image_base64,
                        "status": 0,
                        "seq": 0,
                    },
                },
            }

            headers = {
                "Content-Type": "application/json",
            }

            logger.info(f"HTTP OCR请求URL: {full_url[:150]}...")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(full_url, json=payload, headers=headers)
                logger.info(f"HTTP响应状态码: {response.status_code}")

                if response.status_code == 200:
                    response_data = response.json()
                    logger.info(f"HTTP响应header: {json.dumps(response_data.get('header', {}), ensure_ascii=False)}")

                    if response_data.get("header", {}).get("code") == 0:
                        result_text = self._extract_text_from_response(response_data)
                        
                        if result_text:
                            logger.info(f"HTTP OCR识别完成，文本长度: {len(result_text)}")
                            return result_text, "high"
                        else:
                            logger.warning("OCR识别结果为空")
                            return "", "medium"
                    else:
                        error_msg = response_data.get("header", {}).get("message", "未知错误")
                        logger.error(f"OCR API返回错误: {error_msg}")
                        raise Exception(f"OCR API错误: {error_msg}")
                else:
                    logger.error(f"HTTP请求失败，状态码: {response.status_code}, 响应: {response.text[:500]}")
                    raise Exception(f"HTTP请求失败，状态码: {response.status_code}")

        except Exception as e:
            logger.error(f"HTTP OCR识别失败: {str(e)}", exc_info=True)
            raise

    async def recognize(self, file_path: str) -> Tuple[str, Optional[str]]:
        """
        调用讯飞OCR识别文件（支持图片、PDF、DOCX）
        :param file_path: 文件路径
        :return: (识别文本, 置信度)
        """
        file_type = get_file_type(file_path)
        logger.info(f"开始识别文件: {file_path}, 类型: {file_type}")

        if file_type == "unknown":
            raise Exception(f"不支持的文件类型: {file_path}")

        processed_paths = process_file_for_ocr(file_path)
        
        if not processed_paths:
            raise Exception(f"文件预处理失败，无法生成识别所需的图片: {file_path}")

        all_texts = []
        confidence = "medium"

        for i, path in enumerate(processed_paths):
            logger.info(f"处理第 {i+1}/{len(processed_paths)} 个文件: {path}")
            
            if path.endswith(".txt"):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        text = f.read()
                    if text.strip():
                        all_texts.append(text)
                        confidence = "high"
                except Exception as e:
                    logger.error(f"读取文本文件失败: {str(e)}")
            else:
                try:
                    text, conf = await self._recognize_single_image(path)
                    if text and not text.startswith("（OCR识别结果为空）"):
                        all_texts.append(text)
                        if conf == "high" and confidence != "high":
                            confidence = conf
                except Exception as e:
                    logger.warning(f"识别第 {i+1} 页失败: {str(e)}")

        if not all_texts:
            return "（OCR识别结果为空）", "low"

        full_text = "\n\n".join(all_texts)
        logger.info(f"文件识别完成，总文本长度: {len(full_text)}")
        
        return full_text, confidence


xfyun_ocr_client = XfyunOcrClient()
