#!/usr/bin/env python
from random import randint
import os
from langtrace_python_sdk import langtrace
from pydantic import BaseModel

from crewai.flow.flow import Flow, listen, start

from .crews.researchers.researchers import Researchers
from .crews.writers.writers import Writers

api_key = os.getenv('LANGTRACE_API_KEY')

langtrace.init(api_key=api_key)

class EduFlow(Flow):
    def __init__(self, input_variables=None):
        super().__init__()
        self.input_variables = input_variables or {}

    @start()
    def generate_reseached_content(self):
        out = Researchers().crew().kickoff(self.input_variables).raw
        print(out)
        return out

    @listen(generate_reseached_content)
    def generate_educational_content(self, plan):        
        return Writers().crew().kickoff(self.input_variables).raw

    @listen(generate_educational_content)
    def save_to_markdown(self, content):
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)  # Ensure the directory exists
        
        # Use topic and audience_level from input_variables to create the file name
        topic = self.input_variables.get("topic")
        file_name = f"{topic}.md".replace(" ", "_")  # Replace spaces with underscores
        
        output_path = os.path.join(output_dir, file_name)
        
        with open(output_path, "w") as f:
            f.write(content)

def kickoff(topic=None):
    if topic is None:
        topic = input('Please Enter your topic here: ')
    
    input_variables = {"topic": topic}
    edu_flow = EduFlow(input_variables)
    edu_flow.kickoff()

def plot():
    edu_flow = EduFlow()
    edu_flow.plot()

if __name__ == "__main__":
    kickoff()