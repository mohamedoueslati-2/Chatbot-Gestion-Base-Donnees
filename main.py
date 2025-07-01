import gradio as gr
from groq_functions import *
from mysql_functions import *
from ui_components import create_interface

if __name__ == "__main__":
    app = create_interface()
    app.launch()