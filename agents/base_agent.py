from ollama import chat
import time
import hashlib
import os

class BaseAgent:
    def __init__(self, name, system_prompt, model="qwen2.5:3b", num_predict=500):
        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        self.num_predict = num_predict

    def run(self, task):
        
        cache_key = hashlib.md5(f"{self.system_prompt}{task}".encode("utf-8")).hexdigest()
        cache_dir = "output/cache"
        cache_path = os.path.join(cache_dir, f"{self.name.replace(' ', '_')}_{cache_key}.txt")
        
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                print(f"{self.name} loaded from cache")
                return f.read()

        start = time.time()
        response = chat(
            model=self.model,
            messages=[
                {
                     "role": "system",
                     "content": self.system_prompt
                 },
                 {
                     "role": "user",
                     "content": task
                 }
              ],
              options={
                  "num_predict": self.num_predict
              }
         )
        elapsed = time.time() - start
        print(f"{self.name} took " f"{elapsed:.2f} sec")

        content = response["message"]["content"]
        
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(content)

        return content
