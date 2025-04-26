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

  apiKey: string = "REMOVED-API-KEY";
  geminiApiKey: string = "REMOVED-GEMINI-KEY";
  geminiApiEndpoint: string = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent";

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
    
    // Ping the local endpoint once when the app loads
    this.pingLocalEndpoint();
  }
  
  // Method to ping the local endpoint
  async pingLocalEndpoint() {
    try {
      print("Pinging ngrok endpoint...");
      
      const request = new Request(
        "https://daaa-164-67-70-232.ngrok-free.app/",
        {
          method: "GET",
          headers: {
            "Content-Type": "application/json"
          }
        }
      );
      
      let response = await this.remoteServiceModule.fetch(request);
      print("Endpoint ping status: " + response.status);
      
      if (response.status === 200) {
        let responseData = await response.json();
        print("Endpoint response: " + JSON.stringify(responseData));
      } else {
        print("Endpoint ping failed with status: " + response.status);
      }
    } catch (error) {
      print("Error pinging endpoint: " + error);
    }
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
        contents: [
          {
            parts: [
              {
                text: "You are a helpful AI assistant that works for Snapchat that has access to the view that the user is looking at using Augmented Reality Glasses. The user is asking for help with the following image and text. Keep it short like under 30 words. Be a little funny and keep it positive."
              },
              {
                text: this.textInput.text
              },
              {
                inline_data: {
                  mime_type: "image/jpeg",
                  data: base64Image
                }
              }
            ]
          }
        ],
        generation_config: {
          temperature: 0.2,
          max_output_tokens: 100,
          top_p: 0.95,
          top_k: 40,
          response_mime_type: "text/plain"
        },
        safety_settings: [
          {
            category: "HARM_CATEGORY_HARASSMENT",
            threshold: "BLOCK_MEDIUM_AND_ABOVE"
          },
          {
            category: "HARM_CATEGORY_HATE_SPEECH",
            threshold: "BLOCK_MEDIUM_AND_ABOVE"
          },
          {
            category: "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            threshold: "BLOCK_MEDIUM_AND_ABOVE"
          },
          {
            category: "HARM_CATEGORY_DANGEROUS_CONTENT",
            threshold: "BLOCK_MEDIUM_AND_ABOVE"
          }
        ]
      };
      const fullUrl = `${this.geminiApiEndpoint}?key=${this.geminiApiKey}`;


      const request = new Request(
        fullUrl,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(requestPayload),
        }
      );

      // More about the fetch API: https://developers.snap.com/spectacles/about-spectacles-features/apis/fetch
      let response = await this.remoteServiceModule.fetch(request);
      if (response.status === 200) {
        let responseData = await response.json();
        let responseText;
        try {
          // First try standard response format
          if (responseData.candidates && 
              responseData.candidates[0] && 
              responseData.candidates[0].content && 
              responseData.candidates[0].content.parts && 
              responseData.candidates[0].content.parts[0]) {
            
            responseText = responseData.candidates[0].content.parts[0].text;
          } 
          // Fallback to alternative formats if needed
          else if (responseData.candidates && responseData.candidates[0] && responseData.candidates[0].content) {
            // Try as direct text
            responseText = responseData.candidates[0].content;
          }
          else {
            // Last resort - convert whole response to string
            responseText = JSON.stringify(responseData);
          }
        } catch (e) {
          responseText = "Error parsing response: " + e;
          print("Error extracting response text: " + e);
        }

        this.textOutput.text = responseText;

        print("Response: " + responseText);



        // Show the full model response in the analysis text field
        if (this.LLM_analyse) {
          // Extract useful analysis information
          const fullResponse = responseText;
          const promptTokenEstimate = JSON.stringify(requestPayload).length / 4;
          this.LLM_analyse.text = `Analysis complete ✓\n\nModel: Gemini-1.5-flash\nEstimated tokens: ~${promptTokenEstimate}\n\nFull response:\n${fullResponse}`;
        }
        

        // Call TTS to generate and play speech from the response
        if (this.ttsComponent) {
          this.ttsComponent.generateAndPlaySpeech(
            responseText
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
