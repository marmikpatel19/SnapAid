@component
export class TextToSpeechOpenAI extends BaseScriptComponent {
  @input audioComponent: AudioComponent;
  @input audioOutputAsset: Asset;

  @input
  @widget(
    new ComboBoxWidget()
      .addItem("Alloy", "alloy")
      .addItem("Echo", "echo")
      .addItem("Fable", "fable")
      .addItem("Onyx", "onyx")
      .addItem("Nova", "nova")
      .addItem("Shimmer", "shimmer")
  )
  voice: string = "alloy"; // Default voice selection

  apiKey: string = "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";

  // Remote service module for fetching data
  private remoteServiceModule: RemoteServiceModule = require("LensStudio:RemoteServiceModule");

  onAwake() {
    if (!this.remoteServiceModule || !this.audioComponent || !this.apiKey) {
      print("Remote Service Module, Audio Component, or API key is missing.");
      return;
    }

    if (!this.audioOutputAsset) {
      print(
        "Audio Output asset is not assigned. Please assign an Audio Output asset in the Inspector."
      );
      return;
    }

    this.generateAndPlaySpeech("TextToSpeechOpenAI Ready!");
  }

  public async generateAndPlaySpeech(inputText: string) {
    if (!inputText) {
      print("No text provided for speech synthesis.");
      return;
    }

    try {
      const requestPayload = {
        model: "tts-1",
        voice: this.voice,
        input: inputText,
        response_format: "pcm",
      };

      const request = new Request("https://api.openai.com/v1/audio/speech", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${this.apiKey}`,
        },
        body: JSON.stringify(requestPayload),
      });

      print("Sending request to OpenAI...");

      let response = await this.remoteServiceModule.fetch(request);
      print("Response status: " + response.status);

      if (response.status === 200) {
        try {
          const audioData = await response.bytes();
          print("Received audio data, length: " + audioData.length);

          if (!this.audioOutputAsset) {
            throw new Error("Audio Output asset is not assigned");
          }

          const track = this.getAudioTrackFromData(audioData);
          this.audioComponent.audioTrack = track;
          this.audioComponent.play(1);

          print("Playing speech: " + inputText);
        } catch (processError) {
          print("Error processing audio data: " + processError);
        }
      } else {
        const errorText = await response.text();
        print("API Error: " + response.status + " - " + errorText);
      }
    } catch (error) {
      print("Error generating speech: " + error);
    }
  }

  getAudioTrackFromData = (audioData: Uint8Array): AudioTrackAsset => {
    let outputAudioTrack = this.audioOutputAsset as AudioTrackAsset; // Use the assigned asset
    if (!outputAudioTrack) {
      throw new Error("Failed to get Audio Output asset");
    }

    const sampleRate = 24000;

    const BUFFER_SIZE = audioData.length / 2;
    print("Processing buffer size: " + BUFFER_SIZE);

    var audioOutput = outputAudioTrack.control as AudioOutputProvider;
    if (!audioOutput) {
      throw new Error("Failed to get audio output control");
    }

    audioOutput.sampleRate = sampleRate;
    var data = new Float32Array(BUFFER_SIZE);

    // Convert PCM16 to Float32
    for (let i = 0, j = 0; i < audioData.length; i += 2, j++) {
      const sample = ((audioData[i] | (audioData[i + 1] << 8)) << 16) >> 16;
      data[j] = sample / 32768;
    }

    const shape = new vec3(BUFFER_SIZE, 1, 1);
    shape.x = audioOutput.getPreferredFrameSize();

    // Enqueue audio frames in chunks
    let i = 0;
    while (i < BUFFER_SIZE) {
      try {
        const chunkSize = Math.min(shape.x, BUFFER_SIZE - i);
        shape.x = chunkSize;
        audioOutput.enqueueAudioFrame(data.subarray(i, i + chunkSize), shape);
        i += chunkSize;
      } catch (e) {
        throw new Error("Failed to enqueue audio frame - " + e);
      }
    }

    return outputAudioTrack;
  };
}
