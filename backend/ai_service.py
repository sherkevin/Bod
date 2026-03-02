import os
import json
import re
from openai import OpenAI
from faster_whisper import WhisperModel

import base64

# Configuration
API_KEY = os.getenv("AI_API_KEY", "sk-7870u-nMQ69cSLRmIAxt2A")
BASE_URL = os.getenv("AI_BASE_URL", "https://llmapi.paratera.com/v1")
MODEL_NAME = os.getenv("AI_MODEL_NAME", "DeepSeek-V3.1")
# VLM Model Name (Adjust based on provider capabilities, e.g., gpt-4-vision-preview, qwen-vl-max)
VLM_MODEL_NAME = os.getenv("AI_VLM_MODEL_NAME", "Qwen2.5-VL-7B-Instruct") 

# Initialize LLM Client
client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)

# Initialize ASR Model (Lazily loaded or handled carefully)
asr_model = None

def get_asr_model():
    global asr_model
    if asr_model:
        return asr_model
    
    try:
        print("Loading local ASR model (tiny)...")
        # Try a mirror if possible, or just standard download
        # NOTE: If this fails due to network, we catch it.
        # Mirror: https://hf-mirror.com can be used by setting env var HF_ENDPOINT
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
        
        asr_model = WhisperModel("tiny", device="cpu", compute_type="int8")
        print("ASR Model loaded successfully.")
        return asr_model
    except Exception as e:
        print(f"Failed to load ASR model: {e}")
        return None

def generate_workout_plan(history: list, goal: str) -> dict:
    """
    Generate a workout plan based on user history and goal.
    """
    history_summary = "\n".join([
        f"- {log.get('date')}: {log.get('exercise')} {log.get('weight')}kg x {log.get('sets')}sets x {log.get('reps')}reps"
        for log in history[-10:] # Last 10 workouts
    ])
    
    prompt = f"""
    User Goal: {goal}
    
    Recent Workout History:
    {history_summary}
    
    Based on the above, create a 1-week workout plan. 
    Return a JSON object with this structure:
    {{
        "plan_name": "Name of the plan",
        "overview": "Brief explanation",
        "schedule": [
            {{
                "day": "Monday",
                "focus": "Chest & Triceps",
                "exercises": [
                    {{"name": "Bench Press", "sets": 3, "reps": "8-12", "notes": "Focus on form"}}
                ]
            }}
        ]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an expert fitness coach. Return ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            stream=False
        )
        content = response.choices[0].message.content
        clean_content = re.sub(r'```json\s*|\s*```', '', content).strip()
        return json.loads(clean_content)
    except Exception as e:
        print(f"Plan Gen Error: {e}")
        return {
            "error": str(e),
            "plan_name": "Error Generating Plan",
            "schedule": []
        }

def analyze_workout(text: str) -> dict:
    """
    Analyzes the workout text and returns structured data + feedback.
    """
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": """你是一个专业的健身记录助手。
请从用户的语音文本中提取训练数据，并只需返回一个标准的 JSON 对象，不要包含其他 Markdown 格式。
JSON 格式要求：
{
  "exercise": "动作名称(String)",
  "weight": 重量(Number, 单位kg),
  "sets": 组数(Number, 默认为1),
  "reps": 次数(Number),
  "feedback": "简短鼓励或建议(String, 50字以内)"
}
如果信息缺失，请根据上下文合理推断或留空。"""},
                {"role": "user", "content": text}
            ],
            stream=False
        )
        content = response.choices[0].message.content
        # Try to parse JSON
        try:
             # Strip markdown code blocks if present
            clean_content = re.sub(r'```json\s*|\s*```', '', content).strip()
            data = json.loads(clean_content)
            return data
        except json.JSONDecodeError:
            print(f"JSON Parse Error: {content}")
            return {
                "feedback": content, # Fallback: treat whole response as feedback
                "exercise": None,
                "weight": None,
                "sets": None,
                "reps": None
            }
            
    except Exception as e:
        print(f"AI Error: {e}")
        return {
            "feedback": "AI 服务暂时不可用，但你的记录已保存！",
            "exercise": None,
            "weight": None,
            "sets": None,
            "reps": None
        }

def transcribe_audio(file_path: str) -> str:
    """
    Transcribe audio using local faster-whisper model.
    """
    model = get_asr_model()
    if not model:
        return f"(模拟转写 - 模型加载失败) 用户上传了文件，因网络问题无法下载本地模型。原文件名: {os.path.basename(file_path)}"

    try:
        segments, info = model.transcribe(file_path, beam_size=5)
        
        text = " ".join([segment.text for segment in segments])
        return text
    except Exception as e:
        print(f"ASR Error: {e}")
        return f"(转写失败) {e}"

def encode_image(image_path: str) -> str:
    """Encode image to base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_image(image_path: str) -> dict:
    """
    Analyzes an image using a VLM to identify gym equipment or exercises.
    """
    try:
        base64_image = encode_image(image_path)
        
        response = client.chat.completions.create(
            model=VLM_MODEL_NAME,
            messages=[
                {
                    "role": "system", 
                    "content": """You are a gym assistant. Identify the gym equipment or exercise in the image.
                    Return a JSON object with:
                    - equipment: str (name of equipment, e.g. "Bench Press Station")
                    - exercise: str (likely exercise, e.g. "Bench Press")
                    - muscle_groups: list[str] (target muscles)
                    - usage_tips: str (brief usage tip)
                    
                    Return ONLY JSON."""
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What is this gym equipment?"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500
        )
        
        content = response.choices[0].message.content
        # Try to parse JSON
        try:
            clean_content = re.sub(r'```json\s*|\s*```', '', content).strip()
            data = json.loads(clean_content)
            return data
        except json.JSONDecodeError:
            return {
                "feedback": content,
                "equipment": None,
                "exercise": None
            }
            
    except Exception as e:
        print(f"VLM Error: {e}")
        return {
            "error": str(e),
            "feedback": "Unable to analyze image at the moment."
        }

def generate_speech(text: str, output_path: str) -> str:
    """
    Generate speech from text using OpenAI's TTS API.
    Returns the path to the generated audio file.
    """
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        response.stream_to_file(output_path)
        return output_path
    except Exception as e:
        print(f"TTS Error: {e}")
        return None
