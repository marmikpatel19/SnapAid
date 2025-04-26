import { Interactable } from "../../SpectaclesInteractionKit/Components/Interaction/Interactable/Interactable";
import { InteractorEvent } from "../../SpectaclesInteractionKit/Core/Interactor/InteractorEvent";
import { SIK } from "../../SpectaclesInteractionKit/SIK";
import { TextToSpeechOpenAI } from "./TextToSpeechOpenAI";

@component
export class VisionOpenAI extends BaseScriptComponent {
  @input textInput: Text;
  @input textOutput: Text;
  @input image: Image;
  @input interactable: Interactable;
  @input ttsComponent: TextToSpeechOpenAI;
  @input LLM_analyse: Text;

  apiKey: string = "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";

  // Remote service module for fetching data
  private remoteServiceModule: RemoteServiceModule = require("LensStudio:RemoteServiceModule");

  private isProcessing: boolean = false;

  onAwake() {
    this.createEvent("OnStartEvent").bind(() => {
      this.onStart();
    });
  }

  onStart() {
    let interactionManager = SIK.InteractionManager;

    // Define the desired callback logic for the relevant Interactable event.
    let onTriggerEndCallback = (event: InteractorEvent) => {
      this.handleTriggerEnd(event);
    };

    this.interactable.onInteractorTriggerEnd(onTriggerEndCallback);
  }

  async handleTriggerEnd(eventData) {
    if (this.isProcessing) {
      print("A request is already in progress. Please wait.");
      return;
    }

    if (!this.textInput.text || !this.image || !this.apiKey) {
      print("Text, Image, or API key input is missing");
      return;
    }

    try {
      this.isProcessing = true;
      
      // Set a more detailed analysis text
      if (this.LLM_analyse) {
        const currentTime = new Date().toLocaleTimeString();
        this.LLM_analyse.text = `🔄 Processing (${currentTime})...\n\nSteps:\n1. Encoding image ⏳\n2. Sending to AI model ⏳\n3. Waiting for response ⏳\n\nPlease wait while the AI analyzes your request...`;
      }

      // Access the texture from the image component
      const texture = this.image.mainPass.baseTex;
      if (!texture) {
        print("Texture not found in the image component.");
        return;
      }

      const base64Image = await this.encodeTextureToBase64(texture);

      const requestPayload = {
        model: "gpt-4o-mini",
        messages: [
          {
            role: "system",
            content:
              "You are a helpful AI assistant that works for Snapchat that has access to the view that the user is looking at using Augmented Reality Glasses." +
              " The user is asking for help with the following image and text. Keep it short like under 30 words. Be a little funny and keep it positive.",
          },
          {
            role: "user",
            content: [
              { type: "text", text: this.textInput.text },
              {
                type: "image_url",
                image_url: {
                  url: `data:image/jpeg;base64,${base64Image}`,
                },
              },
            ],
          },
        ],
      };

      const request = new Request(
        "https://api.openai.com/v1/chat/completions",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${this.apiKey}`,
          },
          body: JSON.stringify(requestPayload),
        }
      );
      // More about the fetch API: https://developers.snap.com/spectacles/about-spectacles-features/apis/fetch
      let response = await this.remoteServiceModule.fetch(request);
      if (response.status === 200) {
        let responseData = await response.json();
        this.textOutput.text = responseData.choices[0].message.content;
        
        // Show the full model response in the analysis text field
        if (this.LLM_analyse) {
          // Extract useful analysis information
          const fullResponse = responseData.choices[0].message.content;
          const modelUsed = requestPayload.model;
          const promptTokenEstimate = JSON.stringify(requestPayload).length / 4;
          
          this.LLM_analyse.text = `Analysis complete ✓\n\nModel: ${modelUsed}\nEstimated tokens: ~${promptTokenEstimate}\n\nFull response:\n${fullResponse}`;
        }
        
        print(responseData.choices[0].message.content);

        // Call TTS to generate and play speech from the response
        if (this.ttsComponent) {
          this.ttsComponent.generateAndPlaySpeech(
            responseData.choices[0].message.content
          );
        }
      } else {
        print("Failure: response not successful");
        if (this.LLM_analyse) {
          this.LLM_analyse.text = `❌ Error (HTTP ${response.status})\n\nThe API request failed. Please try again or check your connection.`;
        }
      }
    } catch (error) {
      print("Error: " + error);
      if (this.LLM_analyse) {
        this.LLM_analyse.text = `❌ Error\n\nSomething went wrong: ${error}\n\nPlease try again or check your settings.`;
      }
    } finally {
      this.isProcessing = false;
    }
  }

  // More about encodeTextureToBase64: https://platform.openai.com/docs/guides/vision or https://developers.snap.com/api/lens-studio/Classes/OtherClasses#Base64
  encodeTextureToBase64(texture) {
    return new Promise((resolve, reject) => {
      Base64.encodeTextureAsync(
        texture,
        resolve,
        reject,
        CompressionQuality.LowQuality,
        EncodingType.Jpg
      );
    });
  }
}
