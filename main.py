import argparse
import re

from agent import run_agent, run_lookup



def repl(log_path: str) -> None:
    print("How can I help you? (Type: 'imei no <IMEI>' or just '<IMEI>' or 'quit')")

    while True:
        try:
            user_in = input("> ").strip()
        except EOFError:
            break

        if not user_in:
            continue
        if user_in.lower() in {"quit", "exit", "q"}:
            print("Bye")
            break

        # If the dialogue contains ONLY an IMEI, do IMEI lookup.
        # If it's something else (e.g., 'hi', 'what happened'), do online-style agent response.
        only_imei = re.fullmatch(r"\d{10,17}", user_in)
        if only_imei:
            print(run_lookup(log_path, user_in))
            continue

        m = re.search(r"(?:imei\s*(?:no\s*)?)?(\d{10,17})$", user_in, flags=re.I)
        if m and user_in.lower().startswith("imei"):
            print(run_lookup(log_path, m.group(1)))
            continue

        # default: agent summary/chat
        # If no IMEI is mentioned, only respond when the user explicitly asks a question.
        # Otherwise ignore small talk (e.g., "hi", "how are you").
        if re.search(r"\b(what|why|how|where|status|issue|error|crc|mismatch|location|speed|imei)\b", user_in, flags=re.I):
            print(run_agent(log_path, user_in))
        else:
            print(run_agent(log_path, user_in))







def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="sample.log", help="Path to log file")

    ap.add_argument(
        "--interactive",
        action="store_true",
        help="Dialogue mode (default). Use 'quit' to exit.")

    ap.add_argument("--imei", default=None, help="Lookup: last device data for this IMEI")
    ap.add_argument("--question", default=None, help="Ask a question about the log (offline agent)")

    args = ap.parse_args()

    # If --imei provided, return only the IMEI details (no repl text)
    if args.imei:
        print(run_lookup(args.log, args.imei))
        return

    # If user asked an explicit question, return full summary
    if args.question:
        print(run_agent(args.log, args.question))
        return

    # Default: REPL
    repl(args.log)


if __name__ == "__main__":
    main()

