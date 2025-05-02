SnapAid's an AR app using Snap Inc.’s Spectacles that lets homeless people talk directly to AI (voice, vision, web search) for medical support. Here’s how we did it: 

- We captured audio, image, and location data from the Spectacles
- We created seven workflows for medical help (shelter search, physical injury, medical center search, etc.) using gemini and several LA datasets/apis
- We created an AI orchestration agent with gemini that determines which workflow to execute given the multimodal input

![image](https://github.com/user-attachments/assets/75e2fa3c-aa25-4b65-8545-5b043741d852)
![image](https://github.com/user-attachments/assets/b38b2345-c5d0-410d-9ffc-c71a0eff61d5)
