
import ollama

response = ollama.chat(
    model="llama3.2:latest",
    messages=[
        {
            "role": "user",
            "content": "Explain prompt injection in simple terms."
        }
    ]
)

print(response["message"]["content"])
