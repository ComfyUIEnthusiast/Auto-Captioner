from transformers import AutoProcessor, AutoModelForImageTextToText
import torch
import cv2
import os

os.environ["TRANSFORMERS_NO_PROGRESS_BAR"] = "1"

from transformers.utils import logging
logging.set_verbosity_error()
logging.disable_progress_bar()

videos_dir = os.getenv('VIDEOS_DIR', '../Videos')
custom_prompt = '''
This is the frame of a video. Summarize the frame in enough detail that an AI video generator could recreate it.
If you cannot identify something, do not guess and make something up.
    Cover the following elements: 
        The Actors: 
            What they're wearing.
            How they're interacting.
        Background:
            Describe the general background of the video.
'''
messages = [
    {
        "role": "user",
        "content": [
            {"type": "image"},
            {"type": "text", "text": custom_prompt}
        ]
    }
]

save_dir = "/Models/SmolVLM2-2.2B-Instruct"
model_name = "HuggingFaceTB/SmolVLM2-2.2B-Instruct"
# Download and save locally
if not os.path.exists(save_dir) or not os.listdir(save_dir):
    print("Downloading model into mounted volume...")
    processor = AutoProcessor.from_pretrained(model_name)
    processor.save_pretrained(save_dir)
    model = AutoModelForImageTextToText.from_pretrained(model_name)
    model.save_pretrained(save_dir)
else:
    print("Using existing model from volume.")

device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Using {device}")
#Load model
processor = AutoProcessor.from_pretrained(save_dir)
model = AutoModelForImageTextToText.from_pretrained(save_dir).to(device)
model.eval()

prompt = processor.apply_chat_template(messages, add_generation_prompt=True)

for filename in os.listdir(videos_dir):
    print(f"Processing file: {filename}")
    if not filename.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
        continue
    video_path = os.path.join(videos_dir, filename)
    
    cap = cv2.VideoCapture(video_path)
    captions = []
    
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    sample_rate = int(fps/2) 
    
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_rate == 0:
            print(f"Processing frame: {frame_idx}")
            # Convert BGR (OpenCV) to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Run through model
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": custom_prompt}
                    ]
                }
            ]

            prompt = processor.apply_chat_template(messages, add_generation_prompt=True)

            inputs = processor(
                text=prompt,
                images=rgb_frame,
                return_tensors="pt"
            ).to(device)

            output_ids = model.generate(
                **inputs,
                max_new_tokens=400,
                do_sample=True,
                temperature=0.3
            )
            generated_ids = output_ids[:, inputs["input_ids"].shape[1]:]
            caption = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            
            captions.append(f"Frame {frame_idx}: {caption}")

        frame_idx += 1

    cap.release()
    all_captions_text = "\n".join(captions)
    
    messages = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": f"""
            The following are descriptions of some frames in the video.
            Summarize all of them into a single unified video summary:\n
            {all_captions_text}\n 
            Do not concatenate the captions. Do not repeat the prompts. Describe only one scene.
            Do not repeat concepts and ensure your description does not contradict itself.
            If you cannot identify something, do not guess and make something up, just don't describe it.
            """}
        ]
    }
]

    prompt = processor.apply_chat_template(messages, add_generation_prompt=True)

    inputs = processor(text=prompt, return_tensors="pt").to(device)

    summary_ids = model.generate(
        **inputs,
        max_new_tokens=800,
        do_sample=True,
        temperature=0.3
    )
    generated_ids = summary_ids[:, inputs["input_ids"].shape[1]:]
    summary = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    caption_file = os.path.join(videos_dir, f"{os.path.splitext(filename)[0]}.txt")
    with open(caption_file, "w", encoding="utf-8") as f:
        f.write(summary)

    print(f"Saved captions to {caption_file}")
