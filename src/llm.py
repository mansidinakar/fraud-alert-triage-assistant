import os
import time
from pathlib import Path
import boto3
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')

MODEL_ID = 'us.anthropic.claude-haiku-4-5-20251001-v1:0'
REGION = os.environ.get('AWS_REGION', 'us-east-2')

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client('bedrock-runtime', region_name=REGION)
    return _client


def complete(system, user, max_tokens=600, model_id=MODEL_ID):
    """Call the model once. Returns text plus token counts and latency for cost tracking."""
    start = time.perf_counter()
    resp = _get_client().converse(
        modelId=model_id,
        system=[{'text': system}],
        messages=[{'role': 'user', 'content': [{'text': user}]}],
        inferenceConfig={'maxTokens': max_tokens, 'temperature': 0},
    )
    total_ms = (time.perf_counter() - start) * 1000
    return {
        'text': resp['output']['message']['content'][0]['text'],
        'input_tokens': resp['usage']['inputTokens'],
        'output_tokens': resp['usage']['outputTokens'],
        'latency_ms': round(total_ms),
        'model_id': model_id,
    }


if __name__ == '__main__':
    out = complete('You are a concise assistant.', 'Reply with exactly: Bedrock connection works.')
    print(out)
