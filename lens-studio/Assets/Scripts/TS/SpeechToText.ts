@component
export class SpeechToText extends BaseScriptComponent {
  @input()
  text: Text;
  // Remote service module for fetching data
  private voiceMLModule: VoiceMLModule = require("LensStudio:VoiceMLModule");

  onAwake() {
    let options = VoiceML.ListeningOptions.create();
    options.shouldReturnAsrTranscription = true;
    options.shouldReturnInterimAsrTranscription = true;
    this.voiceMLModule.onListeningEnabled.add(() => {
      this.voiceMLModule.startListening(options);
      this.voiceMLModule.onListeningUpdate.add(this.onListenUpdate);
    });
  }

  onListenUpdate = (eventData: VoiceML.ListeningUpdateEventArgs) => {
    if (eventData.isFinalTranscription) {
      this.text.text = eventData.transcription;
    }
  };
}
