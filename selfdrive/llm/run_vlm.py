from PIL import Image
from google import genai
from google.genai import types
from mcp import ClientSession
from mcp.client.sse import sse_client
from pydantic import BaseModel
import enum
import argparse
import logging
import os
import json

# Set up logging
logging.basicConfig(level=logging.DEBUG)

client = genai.Client(api_key="key")


class AutomationIntent(enum.Enum):
    STOP = "stop"
    SLOW_DOWN = "slow_down"
    SPEED_UP = "speed_up"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    GO_STRAIGHT = "go_straight"

    def __str__(self):
        return self.value

class AlertResponse(BaseModel):
    show: bool
    title: str
    description: str
    intent: AutomationIntent

alert_one_shot_example = """
For example, if the scene is described as "The car is approaching a red traffic light at an intersection with a pedestrian crossing. There are two pedestrians waiting to cross the street on the right side of the car. The lane markings indicate that the car should stop at the red light.", the identified critical objects are "a red traffic light, two pedestrians waiting to cross", and the car's intent is "to stop at the red light", then the alert message could be: "Alert Title: The car is approaching a red traffic light. Alert Description: Please prepare to stop. There are two pedestrians waiting to cross on the right side of the car.
"""

def DescribeScene(img):
    prompt = "You are a autonomous driving labeller. You have access to these front-view camera images. Both image are from the same vehicle, with one in fisheye to provide more visibility. Imagine you are driving the car. Describe the driving scene according to traffic lights, movements of other cars or pedestrians and lane markings."
    response = client.models.generate_content(
        model=model,
        contents=[img, prompt]
    )
    return response

def DescribeObjects(img, model="gemini-2.0-flash"):
    prompt = "You are a autonomous driving labeller. You have access to a front-view camera images of a vehicle.  Both image are from the same vehicle, with one in fisheye to provide more visibility. Imagine you are driving the car. What other road users should you pay attention to in the driving scene? List two or three of them, specifying its location within the image of the driving scene and provide a short description of the that road user on what it is doing, and why it is important to you."
    response = client.models.generate_content(
        model=model,
        contents=[img, prompt]
    )
    return response

def DescribeOrUpdateIntent(img, model="gemini-2.0-flash"):
    prompt = "You are a autonomous driving labeller. You have access to a front-view camera images of a vehicle. Both image are from the same vehicle, with one in fisheye to provide more visibility. Imagine you are driving the car. Based on the lane markings and the movement of other cars and pedestrians, describe the desired intent of the ego car. Is it going to follow the lane to turn left, turn right, or go straight? Should it maintain the current speed or slow down or speed up?"
    response = client.models.generate_content(
        model=model,
        contents=[img, prompt]
    )
    return response

def GenerateAlertMessage(
                        scene_description,
                        object_description,
                        intent_description,
                        onshot_example=False,
                        model="gemini-2.0-flash"):
    sys_msg = "You are an autonomous driving alert system. You will be given a textual description of the driving scene, a list of critical objects in the scene, and the car's intent. Based on these inputs, generate an alert message that summarizes the situation and provides guidance for safe driving. Be short and concise, focusing on the most critical information that the driver needs to be aware of. The alert message should be clear and actionable, helping the driver to make informed decisions while driving. If no critical objects are identified, the alert message should not be generated."
    prompt = f""""
You are an autonomous driving alert system. The current driving scene is described as follows
The scene is described as follows: {scene_description}.
The identified critical objects are {object_description}.
The car's intent is {intent_description}.
{onshot_example if onshot_example else ""}
    """
    response = client.models.generate_content(
        model=model,
        config=types.GenerateContentConfig(
            system_instruction=sys_msg,
            response_mime_type="application/json",
            response_schema=AlertResponse
        ),
        contents=[prompt]
    )
    return response

def main(args):
    image = Image.open(args.image_path)

    scene_description = DescribeScene(image, model=args.model)
    if scene_description is None:
        logging.error("Failed to describe the scene.")
        return
    scene_description = scene_description.text
    logging.debug(f"Scene Description: {scene_description}")

    object_description = DescribeObjects(image, model=args.model)
    if object_description is None:
        logging.error("Failed to describe the objects.")
        return
    object_description = object_description.text
    logging.debug(f"Object Description: {object_description}")

    intent_description = DescribeOrUpdateIntent(image, model=args.model)
    if intent_description is None:
        logging.error("Failed to describe or update the intent.")
        return
    intent_description = intent_description.text
    logging.debug(f"Intent Description: {intent_description}")
    logging.debug("Generating alert message...")

    alert_message = GenerateAlertMessage(
        scene_description=scene_description,
        object_description=object_description,
        intent_description=intent_description,
        onshot_example=True,
        model=args.model
    )
    if alert_message is None:
        logging.error("Failed to generate alert message.")
        return
    logging.debug(f"Alert Message: {alert_message.parsed}")
    print(alert_message)

    # write run to file
    output_file = f"out/alert_{os.path.basename(args.image_path)}.json"
    json_output = {
        "scene_description": scene_description,
        "object_description": object_description,
        "intent_description": intent_description,
        "alert_message": json.loads(alert_message.text) if alert_message.parsed else None
    }
    with open(output_file, "w", encoding='utf-8') as f:
        f.write(json.dumps(json_output, indent=4))
    logging.info(f"Output written to {output_file}")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run VLM for autonomous driving scene analysis.")
    parser.add_argument("--image_path", type=str, required=True, help="Path to the input image.")
    parser.add_argument("--model", type=str, default="gemini-2.0-flash", help="Model to use for analysis.")
    args = parser.parse_args()
    main(args)