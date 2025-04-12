import gradio as gr

from morse_tools import text_to_morse_video

with gr.Blocks(title="Morse Coder", css=".app { max-width: 100% !important; }") as app:
    input_text = gr.Text()

    with gr.Accordion("Settings", open=False):
        wpm_slider = gr.Slider(label="Words Per Minute", minimum=1, value=10, maximum=100, step=1)

    generate_btn = gr.Button("Generate")
    
    output_video = gr.Video()

    generate_btn.click(text_to_morse_video, inputs=[input_text, wpm_slider], outputs=[output_video])


app.launch()