from ollama import chat
import time

start = time.time()

response = chat(
    model="qwen3:4b",
    messages=[
        {
            "role": "user",
            "content": "What is Python?"
        }
    ]
)

print(response["message"]["content"])

end = time.time()

print(f"\nTime taken: {end-start:.2f} seconds")
