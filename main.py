import os
import re
import json
from typing import Optional

from time import sleep
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
chat_model = os.getenv("CHAT_MODEL")

raw_llm = ChatGroq(api_key=api_key, model=chat_model,temperature=0)


def chat_with_model(user_message: str) -> str:
    response = raw_llm.invoke([HumanMessage(content=user_message)])
    return response.content


def read_pm2_log(
    path: str = "/home/amartya-mandal/.pm2/logs/gps-server-out.log",
    last_n_lines: int = 200
) -> str:
    """
    Read live PM2 logs.
    """

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"PM2 log file not found: {path}"
        )

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    return "".join(lines[-last_n_lines:])

def read_sample_log(path: str = "sample.log", last_n_lines: int = 200) -> str:
    """Read sample log content.

    By default returns only the last N lines to keep prompts small.
    """

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Log file not found: {path}. Put sample.log in the project root."
        )

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    if last_n_lines is None or last_n_lines <= 0:
        return "".join(lines)

    return "".join(lines[-last_n_lines:])


def build_log_analysis_prompt(log_text: str) -> str:
    return (
        "You are a deterministic GPS log parser.\n\n"

        "Extract only unique GPS movement records from the logs.\n"
        "Do not generate summaries, explanations, insights, warnings, notes, or extra text.\n"
        "Return ONLY a single fixed-width ASCII table.\n\n"

        "LOG START\n"
        f"{log_text}\n"
        "LOG END\n\n"

        "DIRECTION MAPPING RULES:\n"
        "- 0 to 22 = North\n"
        "- 23 to 67 = North-East\n"
        "- 68 to 112 = East\n"
        "- 113 to 157 = South-East\n"
        "- 158 to 202 = South\n"
        "- 203 to 247 = South-West\n"
        "- 248 to 292 = West\n"
        "- 293 to 337 = North-West\n"
        "- 338 to 360 = North\n\n"

        "FILTERING RULES:\n"
        "- Ignore duplicate consecutive latitude and longitude pairs.\n"
        "- Keep only the first occurrence of repeated coordinates.\n"
        "- Ignore rows with invalid or missing GPS values.\n"
        "- Keep rows in the same order as the logs.\n"
        "- Do not reorder rows.\n\n"

        "TABLE RULES:\n"
        "- Output ONLY the ASCII table.\n"
        "- Do not output markdown.\n"
        "- Do not output bullet points.\n"
        "- Do not output explanations.\n"
        "- Do not output Python code.\n"
        "- Use only '+' '-' and '|' characters for borders.\n"
        "- Keep all columns perfectly aligned.\n"
        "- Use fixed-width formatting.\n"
        "- Round latitude and longitude to 6 decimal places.\n"
        "- Keep speed and course as integers.\n\n"

        "TABLE COLUMNS:\n"
        "IMEI | Direction | Latitude | Longitude | Speed | Course\n\n"

        "EXPECTED OUTPUT FORMAT:\n"
        "+-----------------+-------------+------------+------------+-------+--------+\n"
        "| IMEI            | Direction   | Latitude   | Longitude  | Speed | Course |\n"
        "+-----------------+-------------+------------+------------+-------+--------+\n"
        "| 867440069564326 | North       | 22.571652  | 88.467784  | 10    | 5442   |\n"
        "| 867440069564326 | North-East  | 22.572347  | 88.467297  | 28    | 5461   |\n"
        "+-----------------+-------------+------------+------------+-------+--------+\n"
    )

if __name__ == "__main__":

    print("Simple AI Assistant")
    print("Commands: 'show log', 'analyze log', 'quit'\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        text = user_input.lower()

        if "quit" in text or "exit" in text or "bye" in text or "tata" in text or "q" in text:
            print("Goodbye!")
            break
        #Show log command
        if any(
            word in text
            for word in ["show"]
        ):
            try:
                print("Assistant: Displaying last 200 lines of sample log:")
                sleep(2)  # Simulate thinking time
                print(read_pm2_log())
            except Exception as e:
                print(f"Assistant: {e}")
            continue

        #Analyze log command
        if any(
            word in text
            for word in ["analyze","summarize","extract","pattern","decode"]
        ):
            try:
                print("Assistant: Analyzing log, please wait...")
                sleep(3)  # Simulate longer processing time
                log_text = read_pm2_log()
                prompt = build_log_analysis_prompt(log_text)
                print("Assistant:", chat_with_model(prompt))
            except Exception as e:
                print(f"Assistant: {e}")
            print()
            continue

        # Default: regular chat
        print("Assistant:", chat_with_model(user_input))
        print()

