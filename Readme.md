wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx -P voices/

wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json -P voices/

<!-- Hindi Ones are below -->

mkdir -p voices

# 🔥 Hindi voice (rohan - best one)

wget https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/rohan/medium/hi_IN-rohan-medium.onnx -P voices/

wget https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/rohan/medium/hi_IN-rohan-medium.onnx.json -P voices/

<!-- To test hindi audio -->

echo "नमस्ते आप कैसे हैं" | ./piper/piper \
 --model voices/hi_IN-rohan-medium.onnx \
 --output_file test_hi.wav

aplay test_hi.wav
