from ollama import chat
import time

class BaseAgent:
    def __init__(self, name, system_prompt, model="qwen2.5:3b", num_predict=500):
        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        self.num_predict = num_predict

    def run(self, task):
        
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
        elapsed = time.time()
        print(f"{self.name} took" f"{elapsed:.2f} sec")

        return response["message"]["content"]
