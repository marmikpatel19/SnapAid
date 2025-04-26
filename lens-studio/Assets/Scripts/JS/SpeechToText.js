// @input Component.Text text

// Remote service module for fetching data
var voiceMLModule = require("LensStudio:VoiceMLModule");

script.createEvent("OnStartEvent").bind(() => {
    let options = VoiceML.ListeningOptions.create();
    options.shouldReturnAsrTranscription = true;
    options.shouldReturnInterimAsrTranscription = true;

    voiceMLModule.onListeningEnabled.add(() => {
        voiceMLModule.startListening(options);
        voiceMLModule.onListeningUpdate.add(onListenUpdate);
    });
});

function onListenUpdate(eventData) {
    if (eventData.isFinalTranscription) {
        script.text.text = eventData.transcription;
    }
}