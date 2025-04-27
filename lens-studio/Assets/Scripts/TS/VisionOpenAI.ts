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
  
  // Chat history display
  @input chatHistoryText: Text; // Reference to popup1 text element
  @input maxHistoryLength: number = 10; // Maximum number of conversation pairs to store
  
  // Gemini summary
  @input enableSummary: boolean = true; // Option to enable/disable summaries
  
  // Maximum characters per line for proper text wrapping
  @input maxCharsPerLine: number = 100;

  // Location properties
  latitude: number;
  longitude: number;
  private locationService: LocationService;
  private updateLocationEvent: DelayedCallbackEvent;
  
  // Chat history storage
  private chatHistory: string[] = [];

  apiKey: string = "REMOVED-API-KEY";
  geminiApiKey: string = "REMOVED-GEMINI-KEY";
  geminiApiEndpoint: string = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent";
  python_ngrok_backend: string = "https://7ec3-164-67-70-232.ngrok-free.app";

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
    
    // Initialize chat history display
    this.updateChatHistoryDisplay();
  }

  // Utility function to make text wrap within a textbox
  makeTextWrappable(text: string): string {
    if (!text) return "";
    
    // Split by existing newlines first
    const paragraphs = text.split("\n");
    let result = [];
    
    for (const paragraph of paragraphs) {
      if (paragraph.length <= this.maxCharsPerLine) {
        result.push(paragraph);
        continue;
      }
      
      // Break long paragraphs into wrapped lines
      let remainingText = paragraph;
      while (remainingText.length > 0) {
        // If remaining text is shorter than max length, just add it
        if (remainingText.length <= this.maxCharsPerLine) {
          result.push(remainingText);
          break;
        }
        
        // Find the last space within the max line length
        let cutPoint = remainingText.lastIndexOf(" ", this.maxCharsPerLine);
        if (cutPoint === -1 || cutPoint === 0) {
          // No appropriate space found, force cut at max length
          cutPoint = this.maxCharsPerLine;
        }
        
        result.push(remainingText.substring(0, cutPoint));
        remainingText = remainingText.substring(cutPoint + 1); // +1 to skip the space
      }
    }
    
    return result.join("\n");
  }
  
  // Add a new conversation to the chat history
  addToHistory(userQuery: string, response: string) {
    // Create a formatted conversation entry
    const historyEntry = `User: ${userQuery}\nSnapAid: ${response}\n`;
    
    // Add to the history array
    this.chatHistory.push(historyEntry);
    
    // If we exceed the maximum history length, remove the oldest entries
    if (this.chatHistory.length > this.maxHistoryLength) {
      this.chatHistory = this.chatHistory.slice(this.chatHistory.length - this.maxHistoryLength);
    }
    
    // Update the history display
    this.updateChatHistoryDisplay();
  }
  
  // Update the chat history display in the popup1 text element
  updateChatHistoryDisplay() {
    if (!this.chatHistoryText) {
      print("Chat history text element not assigned");
      return;
    }
    
    // Join all history entries and make them wrappable
    const fullHistory = this.chatHistory.join("\n");
    this.chatHistoryText.text = this.makeTextWrappable(fullHistory);
  }
  
  // Get the full chat history as a single string (for including in prompts)
  getChatHistoryString(): string {
    return this.chatHistory.join("\n");
  }
  
  // Generate summary with Gemini API and add to response
  async generateBulletSummary(responseText: string): Promise<{fullText: string, summaryOnly: string}> {
    if (!this.enableSummary) {
      print("Summary generation disabled");
      return {                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    
        fullText: responseText,
        summaryOnly: ""
      };
    }
    
    try {
      print("Generating bullet-point summary with Gemini...");
      
      const prompt = `List down the key points covered from this response in 3-5 concise bullet points:
"${responseText}"

Format the output as bullet points starting with • and keep each bullet very brief.`;
      
      const geminiPayload = {
        contents: [
          {
            parts: [
              { text: prompt }
            ]
          }
        ],
        generationConfig: {
          temperature: 0.2,
          maxOutputTokens: 200
        }
      };
      
      // Add API key as query parameter
      const geminiUrl = `${this.geminiApiEndpoint}?key=${this.geminiApiKey}`;
      
      const request = new Request(
        geminiUrl,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(geminiPayload),
        }
      );
      
      const response = await this.remoteServiceModule.fetch(request);
      
      if (response.status === 200) {
        const responseData = await response.json();
        
        // Extract the summary text from Gemini response
        if (responseData && 
            responseData.candidates && 
            responseData.candidates[0] && 
            responseData.candidates[0].content && 
            responseData.candidates[0].content.parts && 
            responseData.candidates[0].content.parts[0] && 
            responseData.candidates[0].content.parts[0].text) {
          
          let summaryText = responseData.candidates[0].content.parts[0].text;
          
          // Make sure the summary text is properly formatted for display
          // Clean up any extra whitespace and ensure proper bullet formatting
          summaryText = summaryText.trim()
            .replace(/\n{3,}/g, "\n\n")   // Remove excessive newlines
            .replace(/[•*-] /g, "• ");     // Standardize bullet points
          
          print("Summary generated successfully: " + summaryText);
          print("Summary length: " + summaryText.length + " characters");
          
          // Prepare a clean summary text that's easier to render
          const cleanSummary = "KEY POINTS:\n\n" + summaryText;
          
          return {
            fullText: `${responseText}\n\n---KEY POINTS---\n${summaryText}`,
            summaryOnly: cleanSummary
          };
        } else {
          print("Invalid Gemini response format");
          return {
            fullText: responseText,
            summaryOnly: ""
          };
        }
      } else {
        print("Gemini API call failed with status " + response.status);
        return {
          fullText: responseText,
          summaryOnly: ""
        };
      }
    } catch (error) {
      print("Error in generateBulletSummary: " + error);
      return {
        fullText: responseText,
        summaryOnly: ""
      };
    }
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
    
    // Save the user's query for adding to history later
    const userQuery = this.textInput.text;
  
    try {
      this.isProcessing = true;
      
      // Update UI
      if (this.LLM_analyse) {
        const processingMessage = "Hold on, conducting using your surroundings to fetch tailored responses...";
        this.LLM_analyse.text = this.makeTextWrappable(processingMessage);
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
        user_prompt: userQuery,
        latitude: this.latitude || 0,
        longitude: this.longitude || 0,
        image_surroundings: base64Image,
        chat_history: this.getChatHistoryString() // Include chat history in the request
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
        let responseData;
        let responseText = "";
        
        try {
          // Parse the JSON response first
          responseData = await response.json();
          print("Parsed JSON response successfully");
          
          // Get response text from either response property or full object
          if (responseData && typeof responseData === 'object' && responseData.response !== undefined) {
            print("Found 'response' property in parsed JSON");
            responseText = responseData.response;
          } else {
            // Use the entire responseData object as the response text
            print("No 'response' property found, using entire JSON");
            responseText = typeof responseData === "string" ? responseData : JSON.stringify(responseData);
          }
          
          // Store original response for history
          const originalResponse = responseText;
          
          // Generate summary with Gemini if enabled and append to response
          if (this.enableSummary && responseText) {
            const result = await this.generateBulletSummary(responseText);
            
            // Show ONLY the key points in textOutput with improved rendering
            if (result.summaryOnly) {
              // Ensure text is properly formatted for display
              const displayText = result.summaryOnly;
              this.textOutput.text = this.makeTextWrappable(displayText);
              
              // Debug log
              print("Setting textOutput with summary, length: " + displayText.length);
              
              // Add to history using the summary instead of full response
              this.addToHistory(userQuery, displayText);
            } else {
              // Fallback if summary generation failed
              this.textOutput.text = this.makeTextWrappable(responseText);
              
              // Use original text for history when summary fails
              this.addToHistory(userQuery, responseText);
            }
          } else {
            // No summary - just show response in textOutput
            this.textOutput.text = responseText;
            
            // Add to history using the original response
            this.addToHistory(userQuery, responseText);
          }
          
          print("Response from orchestrate: " + responseText);
          
        } catch (jsonError) {
          print("Error parsing JSON: " + jsonError);
          let errorText = "Error parsing response: " + jsonError;
          this.textOutput.text = this.makeTextWrappable(errorText);
        }

        // Clear analysis field after response is received
        if (this.LLM_analyse) {
          this.LLM_analyse.text = "";
        }

        // Optionally, TTS
        if (this.ttsComponent) {
          // Use responseText if available, otherwise try to access responseData.response
          let textToSpeak = "";
          if (responseData && typeof responseData === 'object' && responseData.response) {
            textToSpeak = responseData.response;
          } else if (typeof responseData === 'string') {
            textToSpeak = responseData;
          } else {
            textToSpeak = JSON.stringify(responseData);
          }
          this.ttsComponent.generateAndPlaySpeech(textToSpeak);
        }
  
      } else {
        print("Failure: Orchestrate API call failed with status " + response.status);
        if (this.LLM_analyse) {
          const errorText = `❌ Error (HTTP ${response.status})\n\nBackend request failed.`;
          this.LLM_analyse.text = this.makeTextWrappable(errorText);
        }
      }
  
    } catch (error) {
      print("Error in handleTriggerEnd: " + error);
      if (this.LLM_analyse) {
        const errorText = `❌ Error\n\n${error}`;
        this.LLM_analyse.text = this.makeTextWrappable(errorText);
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
