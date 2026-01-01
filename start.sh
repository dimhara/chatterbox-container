    
#!/bin/bash

# Default to multilingual if not set
APP_TYPE="${APP_TYPE:-multilingual}"

echo "Starting Chatterbox Container..."
echo "Selected App Type: $APP_TYPE"

if [ "$APP_TYPE" = "standard" ]; then
    echo "Launching Gradio Standard App..."
    python gradio_tts_app.py
elif [ "$APP_TYPE" = "multilingual" ]; then
    echo "Launching Multilingual App..."
    python multilingual_app.py
elif [ "$APP_TYPE" = "vc" ]; then
    echo "Launching Voice Conversion App..."
    python gradio_vc_app.py
else
    echo "Unknown APP_TYPE. Defaulting to Multilingual."
    python multilingual_app.py
fi

  
