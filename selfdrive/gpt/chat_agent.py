#!/usr/bin/env python3
import cereal.messaging as messaging
import openai


def main():
    sm = messaging.SubMaster(['customReserved3'], poll='customReserved3')
    pm = messaging.PubMaster(['customReserved3'])

    while True:
        sm.update(100)
        if sm.updated['customReserved3']:
            chat_prompt = sm['customReserved3'].gptChat
            if not chat_prompt:
                continue
            dat = messaging.new_message('customReserved3')
            try:
                response = openai.completions.create(
                    model="gpt-4",
                    messages=[
                        {
                        "role": "system",
                        "content": (
                            "You are a navigation assistant specialized in providing directions, traffic updates, "
                            "information about nearby places, and safe driving tips. Respond clearly and concisely."
                        ),
                        },
                        {"role": "system", "content": "The User is at {}".format("3808 USF Palm Dr, Tampa, FL 33620")},
                        {"role": "user", "content": chat_prompt},
                    ],
                    temperature=0.7,
                    )
                dat.customReserved3.gptResponse = response["choices"][0]["message"]["content"]
                pm.send('customReserved3', dat)
            except Exception as e:
                dat.customReserved3.gptResponse = "Sorry, I am not able to answer that question."
                print(e)



if __name__ == "__main__":
  main()
