import os
from dotenv import load_dotenv
from deepgram import DeepgramClient, PrerecordedOptions, FileSource, UrlSource

load_dotenv()

def transcribe_audio(source: str) -> str:
    
    try:
        deepgram = DeepgramClient(api_key=os.getenv('DEEPGRAM_API_KEY'))

        options = PrerecordedOptions(
            model="nova-3",
            smart_format=True,
        )

        if source.startswith("http://") or source.startswith("https://"):
            payload: UrlSource = {"url": source}
            response = deepgram.listen.rest.v("1").transcribe_url(payload, options)
        else:
            with open(source, "rb") as file:
                buffer_data = file.read()
            payload: FileSource = {"buffer": buffer_data}
            response = deepgram.listen.rest.v("1").transcribe_file(payload, options)

        transcript = response.results.channels[0].alternatives[0].transcript
        return transcript

    except Exception as e:
        print(f"Exception during transcription: {e}")
        return ""


# if __name__ == "__main__":
    # print("From file:\n", transcribe_audio("Power_English_Update.mp3"))
    # print("\nFrom URL:\n", transcribe_audio("https://pronunciationstudio.com/wp-content/uploads/2016/02/Audio-Introduction-0.1.mp3"))
