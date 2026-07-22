"""测试讯飞OCR API - 使用正确的格式"""
import asyncio
import base64
import hashlib
import hmac
import json
import time
import urllib.parse

import httpx

APPID = "5fac6468"
API_SECRET = "Y2M1YTQ2YThjN2JkMmFjZmFhNWE2NDM1"
API_KEY = "55146bdddb5b7b75757b5348faa867d2"
OCR_URL = "https://cbm01.cn-huabei-1.xf-yun.com/v1/private/se75ocrbm"


async def test_http():
    """测试HTTP方式 - 使用正确的格式"""
    print("=== 测试 HTTP POST 方式 ===")
    image_path = "./uploads/11939ff3-28b2-4c17-9518-ab9242d63e5a.png"
    
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    image_base64 = base64.b64encode(image_data).decode("utf-8")
    print(f"图片大小: {len(image_data)} bytes")
    print(f"Base64后大小: {len(image_base64)} bytes")
    
    date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
    parsed_url = urllib.parse.urlparse(OCR_URL)
    host = parsed_url.hostname
    path = parsed_url.path
    
    print(f"\n=== 签名参数 ===")
    print(f"host: {host}")
    print(f"date: {date}")
    print(f"path: {path}")
    
    signature_origin = f"host: {host}\ndate: {date}\nPOST {path} HTTP/1.1"
    print(f"\n签名原文:")
    print(repr(signature_origin))
    
    signature_sha = hmac.new(
        API_SECRET.encode("utf-8"),
        signature_origin.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    signature = base64.b64encode(signature_sha).decode("utf-8")
    
    authorization_origin = (
        f'api_key="{API_KEY}", '
        f'algorithm="hmac-sha256", '
        f'headers="host date request-line", '
        f'signature="{signature}"'
    )
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
    
    params = {
        "authorization": authorization,
        "date": date,
        "host": host,
    }
    
    full_url = f"{OCR_URL}?{urllib.parse.urlencode(params)}"
    
    payload = {
        "header": {
            "app_id": APPID,
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
    
    print(f"\n请求URL: {full_url[:150]}...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(full_url, json=payload, headers=headers)
            print(f"\n响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"\n响应内容:")
                print(json.dumps(response_data, ensure_ascii=False, indent=2))
                
                if "payload" in response_data and "result" in response_data["payload"]:
                    result = response_data["payload"]["result"]
                    print(f"\n=== 解析结果 ===")
                    print(f"result 类型: {type(result)}")
                    print(f"result 键: {list(result.keys()) if isinstance(result, dict) else '非字典'}")
                    
                    if "text" in result:
                        text_b64 = result["text"]
                        print(f"text 字段长度: {len(text_b64)}")
                        if text_b64:
                            try:
                                decoded_text = base64.b64decode(text_b64).decode("utf-8")
                                print(f"解码后文本内容:\n{decoded_text[:1000]}")
                            except Exception as e:
                                print(f"解码失败: {str(e)}")
                            else:
                                print(f"\n文本总长度: {len(decoded_text)}")
                        else:
                            print("text 字段为空")
            else:
                print(f"\n响应内容: {response.text[:2000]}")
        except Exception as e:
            print(f"请求失败: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_http())
