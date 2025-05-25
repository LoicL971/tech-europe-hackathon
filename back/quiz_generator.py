import os
from typing import List, Tuple
from mistralai import Mistral
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

class QuestionsAnswers(BaseModel):
    questions: list[str]
    answers: list[str]


class QuizGenerator:
    def __init__(self, api_key: str):
        """Initialize the QuizGenerator with Mistral API key."""
        self.client = Mistral(api_key=api_key)

    def generate_feedback(self, markdown_text: str, question: str, right_answer: str, user_answer: str) -> str:
        """
        Generate feedback for a user's answer by comparing it with the correct answer.

        Args:
            markdown_text (str): The original text the question was based on
            question (str): The question that was asked
            right_answer (str): The correct answer
            user_answer (str): The user's submitted answer

        Returns:
            str: Brief feedback about the user's answer
        """
        prompt = (
            'Give a one-sentence personalized feedback on the answer. Use "you" and "your" to make it more personal.\n'
            'If the answer is correct, start with encouraging phrases like "Well done!", "Great job!", or "Let\'s go!" before giving the feedback.\n'
            'If the answer is incorrect or incomplete, start with encouraging phrases like "No worries!", "Keep going!", or "You\'re getting there!" before explaining what was wrong.\n'
            'Include a precise answer when the user\'s answer is incorrect or incomplete but explain shortly why the user\'s answer is wrong. Do not complicate the answer.\n'
            'If the answer is correct but too detailed, suggest how to make it more concise.\n\n'
            'Context:\n' + markdown_text + '\n\n'
            'Question: ' + question + '\n'
            'Correct answer: ' + right_answer + '\n'
            'Your answer: ' + user_answer + '\n\n'
            'Keep it to one sentence and make it encouraging. If the answer is wrong, include the correct answer:'
        )

        messages = [
            {"role": "system", "content": "You are a supportive teacher providing personalized, encouraging feedback on answers. Always include the correct answer when the user's answer is wrong."},
            {"role": "user", "content": prompt}
        ]

        chat_response = self.client.chat.complete(
            model="mistral-large-latest",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )

        return chat_response.choices[0].message.content

    def generate_follow_up_questions(self,
                                    markdown_text: str,
                                    previous_questions: List[str],
                                    previous_answers: List[str],
                                    previous_feedback: List[str],
                                    num_follow_ups: int = 3) -> Tuple[List[str], List[str]]:
        """
        Generate follow-up questions based on previous answers and user profile.

        Args:
            markdown_text (str): The original text
            previous_questions (List[str]): List of previously asked questions
            previous_answers (List[str]): List of user's answers to previous questions
            previous_feedback (List[str]): List of feedback given for previous answers
            num_follow_ups (int): Number of follow-up questions to generate

        Returns:
            Tuple[List[str], List[str]]: List of follow-up questions and their answers
        """
        # Create context from previous Q&A and feedback
        qa_context = "\n".join([
            "Q: " + q + "\nA: " + a + "\nFeedback: " + f
            for q, a, f in zip(previous_questions, previous_answers, previous_feedback)
        ])

        prompt = (
            'Based on the following context, previous questions/answers, and feedback, generate ' + str(num_follow_ups) + ' follow-up questions and answers.\n'
            'The questions should address the specific areas where the user needs improvement based on the feedback.\n'
            'Focus on generating questions that will help the user better understand the concepts they struggled with.\n\n'
            'Original text:\n' + markdown_text + '\n\n'
            'Previous Q&A and Feedback:\n' + qa_context + '\n\n'
            'Generate follow-up questions and answers that:\n'
            '1. Address specific misconceptions or gaps identified in the feedback\n'
            '2. Build upon the user\'s previous answers and the feedback given\n'
            '3. Help clarify concepts that were not fully understood\n'
            '4. Are more specific and targeted based on the feedback\n\n'
            'Format the output as a list of strings representing question and answer pair:\n'
            '{\n'
            '    question: [question1, question2, question3, ...]\n'
            '    answers: [answer1, answer2, answer3, ...]\n'
            '}'
        )

        messages = [
            {"role": "system", "content": "You are an educational AI that generates targeted follow-up questions based on previous answers and feedback."},
            {"role": "user", "content": prompt}
        ]

        chat_response = self.client.chat.parse(
            model="mistral-large-latest",
            messages=messages,
            response_format=QuestionsAnswers,
            temperature=0.7,
            max_tokens=1000
        )
        print("chat anwer", chat_response)

        parsed_response = chat_response.choices[0].message.parsed
        questions_list = parsed_response.questions
        answers_list = parsed_response.answers

        return questions_list[:num_follow_ups], answers_list[:num_follow_ups]

    def generate_report(self, questions: List[str], answers: List[str], feedback: List[str]) -> str:
        """
        Generate a concise report about the user's performance on the quiz.

        Args:
            markdown_text (str): The original text the questions were based on
            questions (List[str]): List of questions asked
            answers (List[str]): List of user's answers
            feedback (List[str]): List of feedback given for each answer

        Returns:
            str: A concise report summarizing the user's performance and areas for improvement
        """
        qa_summary = "\n".join(["Q: " + q + "\nA: " + a + "\nFeedback: " + f for q, a, f in zip(questions, answers, feedback)])

        prompt = (
            'Based on the following questions, answers, and feedback, generate a concise report that:\n'
            '1. Summarizes the user\'s overall performance\n'
            '2. Identifies 2-3 specific areas where the user needs improvement\n'
            '3. Provides brief, actionable suggestions for improvement\n\n'
            'Keep the report short and focused on actionable insights.\n\n'
            'Questions and Answers:\n' + qa_summary + '\n\n'
            'Generate a concise report:'
        )

        messages = [
            {"role": "system", "content": "You are an educational AI that generates concise, actionable performance reports."},
            {"role": "user", "content": prompt}
        ]

        chat_response = self.client.chat.complete(
            model="mistral-large-latest",
            messages=messages,
            temperature=0.7,
            max_tokens=300
        )

        return chat_response.choices[0].message.content

    def generate_questions(self, markdown_text: str, num_questions: int = 4) -> List[Tuple[str, str]]:
        """
        Generate questions and answers from markdown text using Mistral AI.

        Args:
            markdown_text (str): The markdown text extracted from images
            num_questions (int): Number of questions to generate (default: 5)

        Returns:
            List[Tuple[str, str]]: List of (question, answer) pairs
        """
        # Create a prompt for the AI to generate questions and answers
        prompt = (
            'Based on the following text, generate ' + str(num_questions) + ' engaging and fun questions that test understanding of the content.\n'
            'Guidelines for questions:\n'
            '- Make questions interactive and engaging. Add a bit of context to the questions.\n'
            '- Use creative formats like:\n'
            '  * "How would you explain..." challenges\n'
            '  * "Compare and contrast..." analysis\n'
            '  * use "what is..." or "define..." questions\n'
            '- Make questions feel like a conversation rather than a test\n'
            '- Include questions that require critical thinking\n'
            '- Use active and engaging language\n'
            '- Make questions short and concise.\n\n'
            'Format the output as a list of strings representing question and answer pair:\n'
            '{\n'
            '    question: [question1, question2, question3, ...]\n'
            '    answers: [answer1, answer2, answer3, ...]\n'
            '}\n\n'
            'Text:\n' + markdown_text + '\n\n'
            'Questions and answer pairs:'
        )

        # Create chat messages
        messages = [
            {"role": "system", "content": "You are a teacher assistant that generates educational questions from a student lessons."},
            {"role": "user", "content": prompt},
        ]


        chat_response = self.client.chat.parse(
            model="mistral-large-latest",
            messages=messages,
            response_format=QuestionsAnswers,
            temperature=0.7,
            max_tokens=10000
        )

        parsed_response = chat_response.choices[0].message.parsed
        questions_list = parsed_response.questions
        answers_list = parsed_response.answers
        print("Generated questions:", questions_list[:num_questions])
        return questions_list[:num_questions],answers_list[:num_questions]

api_key = os.environ["MISTRAL_API_KEY"]
generator = QuizGenerator(api_key)

def main(input_text):
    questions,answers = generator.generate_questions(input_text)

    print(questions)
    print(answers)
    return questions
