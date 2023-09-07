import argparse
import cv2
import numpy as np
import tensorflow as tf


# Define a function to load the TFLite model
def load_model(model_path):
    interpreter = tf.lite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    return interpreter


# Define a function to preprocess an image for inference
def preprocess_image(image, input_shape):
    resized_image = cv2.resize(image, (input_shape[1], input_shape[0]))
    resized_image = resized_image / 255.0  # Normalize to [0, 1]
    input_tensor = resized_image[np.newaxis, ...].astype(np.float32)
    return input_tensor


# Define a function to perform inference on a video
def inference_on_video(video_path, model, output_path):
    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        input_tensor = preprocess_image(frame, (172, 172))  # Adjust input shape as needed
        model.set_tensor(model.get_input_details()[0]['index'], input_tensor)
        model.invoke()

        output = model.get_tensor(model.get_output_details()[0]['index'])
        # Process the output as needed (e.g., object detection, classification, etc.)
        print(output)

        # Optionally, draw bounding boxes or other annotations on the frame based on the output

        out.write(frame)

    cap.release()
    out.release()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Path to the MoViNet TFLite model")
    parser.add_argument("--video", required=True, help="Path to the input video")
    parser.add_argument("--output", required=True, help="Path to the output video")
    args = parser.parse_args()

    model = load_model(args.model)
    inference_on_video(args.video, model, args.output)
