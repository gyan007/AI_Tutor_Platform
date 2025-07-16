import json
import re
from typing import List
from pydantic import BaseModel, ValidationError, field_validator, model_validator
from ai_tutor_platform.llm.mistral_chain import generate_response


class QuizItem(BaseModel):
    question: str
    options: List[str]
    answer: str

    @field_validator("options")
    def validate_options(cls, options):
        if not isinstance(options, list) or len(options) != 4:
            raise ValueError("There must be exactly 4 options.")
        return [opt.strip(" ,.:;\"") for opt in options]

    @model_validator(mode="after")
    def check_answer_in_options(self):
        answer_clean = self.answer.strip(" ,.:;\"").lower()
        options_clean = [opt.strip(" ,.:;\"").lower() for opt in self.options]
        if answer_clean not in options_clean:
            raise ValueError(f"Answer '{self.answer}' not found in options.")
        return self


def extract_json_array(text: str) -> str:
    # Remove code blocks
    text = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()

    # Extract JSON array
    match = re.search(r'\[\s*{.*?}\s*\]', text, re.DOTALL)
    if not match:
        raise ValueError("No valid JSON array found in LLM output.")
    json_str = match.group(0)

    # Fix common formatting issues
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*]", "]", json_str)
    json_str = json_str.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    json_str = re.sub(r'"\s*"(.*?)"\s*"', r'"\1"', json_str)
    json_str = re.sub(r'\\(?![ntr"\\/bfu])', r'\\\\', json_str)

    return json_str


def clean_dict_keys(data: list) -> list:
    cleaned = []
    for item in data:
        if isinstance(item, dict):
            cleaned_item = {k.strip(): v for k, v in item.items()}
            cleaned.append(cleaned_item)
    return cleaned


def parse_options(raw_options):
    if isinstance(raw_options, str):
        return [opt.strip() for opt in raw_options.split(",") if opt.strip()]
    elif isinstance(raw_options, list):
        return [opt.strip(" ,.:;\"") for opt in raw_options if isinstance(opt, str)]
    return []


def generate_quiz(subject: str, num_questions: int = 5, max_retries: int = 3) -> list:
    prompt_template = (
        "Generate exactly {num} multiple-choice questions on the topic '{subject}'.\n"
        "Each question must have exactly 4 options and one clearly correct answer.\n"
        "The correct answer must be one of the 4 options.\n"
        "Avoid emojis, markdown, LaTeX, or special characters.\n"
        "Respond with ONLY a valid JSON array. No explanation or intro.\n"
        "Example format:\n"
        "[\n"
        "  {{\n"
        "    \"question\": \"What is 2 + 2?\",\n"
        "    \"options\": [\"1\", \"2\", \"3\", \"4\"],\n"
        "    \"answer\": \"4\"\n"
        "  }}\n"
        "]"
    )

    valid_questions = []

    for attempt in range(max_retries):
        needed = num_questions - len(valid_questions)
        if needed <= 0:
            break

        prompt = prompt_template.format(subject=subject, num=needed)

        try:
            raw_output = generate_response(prompt)
            print("\n==== RAW LLM OUTPUT ====\n", raw_output)

            cleaned_json_str = extract_json_array(raw_output)
            print("\n==== CLEANED JSON ====\n", cleaned_json_str)

            quiz_data = json.loads(cleaned_json_str)
            quiz_data = clean_dict_keys(quiz_data)

            for i, item in enumerate(quiz_data):
                try:
                    question = item.get("question", "").strip()
                    raw_options = item.get("options", [])
                    answer = item.get("answer", "").strip()
                    options = parse_options(raw_options)

                    quiz_item = QuizItem(question=question, options=options, answer=answer)

                    valid_questions.append({
                        "question": quiz_item.question,
                        "options": quiz_item.options,
                        "answer": quiz_item.answer.strip(" ,.:;\"")
                    })

                    if len(valid_questions) >= num_questions:
                        break
                except ValidationError as e:
                    print(f"⚠️ Skipped question {i + 1} due to validation error: {e}")

        except Exception as e:
            print(f"💥 Error in LLM attempt {attempt + 1}: {e}")

    if not valid_questions:
        return [{
            "question": "[ERROR] No valid questions could be generated.",
            "options": [],
            "answer": ""
        }]
    elif len(valid_questions) < num_questions:
        return [{
            "question": f"[ERROR] Only {len(valid_questions)} valid questions recovered out of {num_questions} requested.",
            "options": [],
            "answer": ""
        }]

    return valid_questions
