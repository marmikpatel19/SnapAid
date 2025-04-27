import { Interactable } from "../../SpectaclesInteractionKit/Components/Interaction/Interactable/Interactable";
import { InteractorEvent } from "../../SpectaclesInteractionKit/Core/Interactor/InteractorEvent";
import { SIK } from "../../SpectaclesInteractionKit/SIK";
import { TextToSpeechOpenAI } from "./TextToSpeechOpenAI";

// Add location module requirement
require('LensStudio:RawLocationModule');

@component
export class VisionOpenAI extends BaseScriptComponent {
  @input textInput: Text;
  @input textOutput: Text;
  @input image: Image;
  @input interactable: Interactable;
  @input ttsComponent: TextToSpeechOpenAI;
  @input LLM_analyse: Text;

  // Location properties
  latitude: number;
  longitude: number;
  private locationService: LocationService;
  private updateLocationEvent: DelayedCallbackEvent;

  apiKey: string = "REMOVED-API-KEY";
  geminiApiKey: string = "REMOVED-GEMINI-KEY";
  geminiApiEndpoint: string = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent";
  python_ngrok_backend: string = "https://fe4e-2600-387-15-1115-00-b.ngrok-free.app";

  // Remote service module for fetching data
  private remoteServiceModule: RemoteServiceModule = require("LensStudio:RemoteServiceModule");

  private isProcessing: boolean = false;

  onAwake() {
    this.createEvent("OnStartEvent").bind(() => {
      this.onStart();
    });

    // Initialize location update event
    this.updateLocationEvent = this.createEvent('DelayedCallbackEvent');
    this.updateLocationEvent.bind(() => {
      this.updateLocation();
    });
  }

  onStart() {
    let interactionManager = SIK.InteractionManager;

    // Define the desired callback logic for the relevant Interactable event.
    let onTriggerEndCallback = (event: InteractorEvent) => {
      this.handleTriggerEnd(event);
    };

    this.interactable.onInteractorTriggerEnd(onTriggerEndCallback);
    
    // Initialize location service
    this.initLocationService();
  }

  // Initialize location service
  initLocationService() {
    try {
      print("Initializing location service...");
      this.locationService = GeoLocation.createLocationService();
      
      // Try maximum accuracy
      this.locationService.accuracy = GeoLocationAccuracy.Navigation; // Most accurate
      
      // Start location updates immediately
      this.updateLocationEvent.reset(0.0);
      print("Location service initialized successfully");

      // Remove invalid permission check
    } catch (error) {
      print("Error initializing location service: " + error);
    }
  }
  
  // Update location periodically
  updateLocation() {
    if (!this.locationService) {
      print("Location service not initialized");
      return;
    }
    
    //created vision query
    this.locationService.getCurrentPosition(
      (geoPosition) => {
        this.latitude = geoPosition.latitude;
        this.longitude = geoPosition.longitude;
        
        // Enhanced location debugging
        print(`Location updated - Lat: ${this.latitude.toFixed(6)}, Long: ${this.longitude.toFixed(6)}`);
        print(`Location source: ${geoPosition.locationSource}`); // Will show if SIMULATED
        print(`Location timestamp: ${geoPosition.timestamp}`);
        print(`Location accuracy: ${geoPosition.horizontalAccuracy}m`);
      },
      (error) => {
        print("Error getting location: " + error);
      }
    );
    
    // Schedule next update in 1 second
    this.updateLocationEvent.reset(20.0);
  }

  // Method to ping the local endpoint
  // async pingLocalEndpoint() {
  //   try {
  //     print("Pinging ngrok endpoint...");
      
  //     const request = new Request(this.python_ngrok_backend,
  //       {
  //         method: "GET",
  //         headers: {
  //           "Content-Type": "application/json"
  //         }
  //       }
  //     );
      
  //     let response = await this.remoteServiceModule.fetch(request);
  //     print("Endpoint ping status: " + response.status);
      
  //     if (response.status === 200) {
  //       let responseData = await response.json();
  //       print("Endpoint response: " + JSON.stringify(responseData));
  //     } else {
  //       print("Endpoint ping failed with status: " + response.status);
  //     }
  //   } catch (error) {
  //     print("Error pinging endpoint: " + error);
  //   }
  // }

  async handleTriggerEnd(eventData) {
    if (this.isProcessing) {
      print("A request is already in progress. Please wait.");
      return;
    }
  
    if (!this.textInput.text) {
      print("Text input is missing");
      return;
    }
  
    try {
      this.isProcessing = true;
      
      // Update UI
      if (this.LLM_analyse) {
        const currentTime = new Date().toLocaleTimeString();
        this.LLM_analyse.text = `🔄 Processing (${currentTime})...\n\nSteps:\n1. Preparing request ⏳\n2. Sending to backend ⏳\n3. Waiting for response ⏳\n\nPlease wait...`;
      }
  
      let base64Image = "";
  
      // Encode image if available
      if (this.image) {
        const texture = this.image.mainPass.baseTex;
        if (texture) {
          base64Image = await this.encodeTextureToBase64(texture) as string;
          print("Image encoded to base64 successfully.");
        } else {
          print("Texture not found in the image component.");
        }
      }
  
      // Prepare payload
      const orchestratePayload = {
        user_prompt: this.textInput.text,
        latitude: this.latitude || 0,
        longitude: this.longitude || 0,
        image_surroundings: base64Image
      };
  
      const fullUrl = `${this.python_ngrok_backend}/api/orchestrate`;
  
      const request = new Request(
        fullUrl,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(orchestratePayload),
        }
      );
      print("Posting to URL: " + fullUrl);
      let response = await this.remoteServiceModule.fetch(request);
      
      if (response.status === 200) {
        let responseData = await response.json();
  
        let responseText = typeof responseData === "string" ? responseData : JSON.stringify(responseData);
  
        // Set output
        this.textOutput.text = responseText;
        print("Response from orchestrate: " + responseText);
  
        // Update analysis field
        if (this.LLM_analyse) {
          this.LLM_analyse.text = `✅ Response Received\n\n${responseText}`;
        }
  
        // Optionally, TTS
        if (this.ttsComponent) {
          this.ttsComponent.generateAndPlaySpeech(responseText);
        }
  
      } else {
        print("Failure: Orchestrate API call failed with status " + response.status);
        if (this.LLM_analyse) {
          this.LLM_analyse.text = `❌ Error (HTTP ${response.status})\n\nBackend request failed.`;
        }
      }
  
    } catch (error) {
      print("Error in handleTriggerEnd: " + error);
      if (this.LLM_analyse) {
        this.LLM_analyse.text = `❌ Error\n\n${error}`;
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
