import os
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv


load_dotenv()

# Configure the Jinja2 environment
TEMPLATE_FOLDER = os.path.join(os.path.dirname(__file__), "prompt_templates")
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_FOLDER))

# Function to render a Jinja2 template
def render_template(template_name: str, context: dict) -> str:
    template = jinja_env.get_template(template_name)
    return template.render(context)