from ollama import chat


class BaseAgent:
    def __init__(self, name, system_prompt, model="qwen2.5:3b"):
        self.name = name
        self.system_prompt = system_prompt
        self.model = model

    def run(self, task):

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
                  "num_predict": 200
              }
         )

        return response["message"]["content"]
