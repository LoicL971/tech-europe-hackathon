import random
import base64
import mistral_ocr
import os
import tempfile
from datetime import datetime
from typing import TypedDict, Optional
from dataclasses import dataclass
from quiz_generator import QuizGenerator

NUMBER_GENERATED_QUESTION = 4

class Question(TypedDict):
    question: str
    right_answer: str

class AnsweredQuestion(TypedDict):
    question: str
    right_answer: str
    user_answer: str
    feedback: str

class Session(object):
    generator: QuizGenerator
    id: int
    base64_docs: list[str]
    decoded_docs: list[str]
    concatenated_docs: str
    questions_to_ask: list[Question]
    answers_with_feedbacks: list[AnsweredQuestion]

    def __init__(self, generator: QuizGenerator):
        self.generator = generator
        self.id = random.randint(0, 1000000000)
        self.base64_docs = []
        self.decoded_docs = []
        self.concatenated_docs = ""
        self.questions_to_ask = []
        self.followup_questions_to_ask = []
        self.answers_with_feedbacks = []

    def add_doc(self, base64_doc: str):
        """Add a single base64 encoded document to the session"""
        self.base64_docs.append(base64_doc)
        # Decode the base64 document
        decoded_doc = mistral_ocr.process_image_to_text(base64_doc)
        self.decoded_docs.append(decoded_doc)

    def _save_image_to_temp(self, base64_doc: str, index: int) -> str:
        """Save a base64 image to temporary folder for testing purposes"""
        try:
            # Create temp directory if it doesn't exist
            temp_dir = os.path.join(tempfile.gettempdir(), "quiz_images")
            os.makedirs(temp_dir, exist_ok=True)

            # Remove data URL prefix if present
            clean_base64 = base64_doc
            if "," in base64_doc:
                clean_base64 = base64_doc.split(",")[1]

            # Decode base64 to binary
            image_data = base64.b64decode(clean_base64)

            # Create filename with timestamp and session info
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"session_{self.id}_{timestamp}_image_{index}.jpg"
            filepath = os.path.join(temp_dir, filename)

            # Save the image
            with open(filepath, "wb") as f:
                f.write(image_data)

            print(f"✅ Saved image to: {filepath}")
            return filepath

        except Exception as e:
            print(f"❌ Failed to save image {index}: {str(e)}")
            return ""

    def add_docs(self, base64_docs: list[str]):
        """Add multiple base64 encoded documents to the session"""
        self.base64_docs.extend(base64_docs)

        print(f"📸 Received {len(base64_docs)} images for session {self.id}")

        # Print temp directory location for easy access
        temp_dir = os.path.join(tempfile.gettempdir(), "quiz_images")
        print(f"🗂️  Images will be saved to: {temp_dir}")

        for i, base64_doc in enumerate(base64_docs):
            # Save image to temp folder for testing
            saved_path = self._save_image_to_temp(base64_doc, i)

            # Process with OCR
            decoded_doc = mistral_ocr.process_image_to_text(base64_doc)
            self.decoded_docs.append(decoded_doc)

            print(
                f"📄 Processed image {i + 1}/{len(base64_docs)}: {len(decoded_doc)} characters extracted"
            )

        print(
            f"✨ Completed processing {len(base64_docs)} images for session {self.id}"
        )

    def generate_next_question(self) -> str:
        if self.questions_to_ask:
            return self.questions_to_ask[0]["question"]

        if not self.concatenated_docs:
            self.concatenated_docs = ""
            for i, doc in enumerate(self.decoded_docs):
                page_content = f"Page {i + 1}:\n{doc}\n\n"
                self.concatenated_docs += page_content
        questions_list, answers_list = self.generator.generate_questions(
            self.concatenated_docs, NUMBER_GENERATED_QUESTION
        )
        for question, answer in zip(questions_list, answers_list):
            typedQuestion: Question = {"question": question, "right_answer": answer}
            self.questions_to_ask.append(typedQuestion)

        return self.questions_to_ask[0]["question"]

    def generate_next_followup_question(self) -> str:
        if self.followup_questions_to_ask:
            return self.followup_questions_to_ask[0]["question"]

        # Check if we have any answered questions to base follow-up questions on
        if not self.answers_with_feedbacks:
            raise ValueError("Cannot generate follow-up questions without any answered questions. Please answer at least one question first.")

        if not self.concatenated_docs:
            self.concatenated_docs = ""
            for (i, doc) in enumerate(self.decoded_docs):
                page_content = f"Page {i+1}:\n{doc}\n\n"
                self.concatenated_docs += page_content

        # Generate follow-up questions based on previous Q&A and feedback
        questions_list, answers_list = self.generator.generate_follow_up_questions(
            self.concatenated_docs,
            [q["question"] for q in self.answers_with_feedbacks],
            self.previous_answers,
            [a["feedback"] for a in self.answers_with_feedbacks],
            num_follow_ups=5
        )

        # Check if we got any questions back
        if not questions_list or not answers_list:
            raise ValueError("Failed to generate follow-up questions. Please try again or answer more questions first.")

        for question, answer in zip(questions_list, answers_list):
            typedQuestion: Question = {
                "question": question,
                "right_answer": answer
            }
            self.followup_questions_to_ask.append(typedQuestion)

        if not self.followup_questions_to_ask:
            raise ValueError("No follow-up questions were generated. Please try again.")

        return self.followup_questions_to_ask[0]["question"]

    def generate_feedback(self, user_answer):
        # Check if we're answering a follow-up question or regular question
        if self.followup_questions_to_ask:
            current_question = self.followup_questions_to_ask[0]
            feedback = self.generator.generate_feedback(self.concatenated_docs, current_question["question"], current_question["right_answer"], user_answer)
            answered_question: AnsweredQuestion = {
                "feedback": feedback,
                "question": current_question["question"],
                "right_answer": current_question["right_answer"],
                "user_answer": user_answer
            }
            self.answers_with_feedbacks.append(answered_question)
            self.followup_questions_to_ask.pop(0)
            return answered_question["feedback"]
        else:
            current_question = self.questions_to_ask[0]
            feedback = self.generator.generate_feedback(self.concatenated_docs, current_question["question"], current_question["right_answer"], user_answer)
            answered_question: AnsweredQuestion = {
                "feedback": feedback,
                "question": current_question["question"],
                "right_answer": current_question["right_answer"],
                "user_answer": user_answer
            }
            self.answers_with_feedbacks.append(answered_question)
            self.questions_to_ask.pop(0)
            return answered_question["feedback"]

    @property
    def previous_answers(self) -> list[str]:
        """Extract user answers from answered questions"""
        return [answer["user_answer"] for answer in self.answers_with_feedbacks]

    def generate_report(self) -> str:
        return self.generator.generate_report(
            [q["question"] for q in self.answers_with_feedbacks],
            self.previous_answers,
            [a["feedback"] for a in self.answers_with_feedbacks],
        )
